# Backwalk: ModelZip-7B whitepaper (StackMeadow AI, v1.2.0)

**Source:** StackMeadow AI, "ModelZip-7B: Compressed Expertise, Uncompressed Performance," 2026-10-28
**Reviewed:** 2026-11-07 · backwalk · adversarial read of a vendor pitch load-bearing a replacement decision
**Tag:** `modelzip-7b-legal-sum`
**Hardware envelope assumed:** M3 Max · 128GB unified memory · ~20 hours wall-clock this week
**Decision this backwalk feeds:** whether to replace a Llama-3-70B legal-summarization pipeline with ModelZip-7B

> **Note on reading register.** This is an adversarial read: a surface for
> probes, not a verdict. The whitepaper's numbers may reproduce; the model
> may be excellent for this use case. The point here is to know *which
> parts of the pitch are load-bearing for your decision*, which parts
> depend on vendor-controlled measurement, and what the cheapest
> empirical check is per load-bearing assumption. Nothing below
> concludes "use it" or "don't use it." Run the first probe; the answer
> moves.

---

## 1. Claims as stated

The headline sentence compresses four distinct claims. Pulling them apart:

| # | Claim                                                      | Scope / population                                          | Effect size (reported)                         | Qualifier                              |
|---|------------------------------------------------------------|-------------------------------------------------------------|------------------------------------------------|----------------------------------------|
| 1 | "Matches Llama-3-70B on MMLU"                              | MMLU 5-shot                                                 | 78.2 vs 79.5 (-1.3pp)                          | A benchmark named inside the training-refinement pipeline |
| 2 | "10x less inference compute"                               | H100 tokens/sec throughput                                  | ~310 vs ~28 (actually ~11x)                    | Single-GPU, bf16, decoding settings not stated |
| 3 | "7x less training compute"                                 | Training H100-hours                                         | 768 vs 5,500 (public est.)                     | Excludes Llama-3-8B base model pretraining cost |
| 4 | **"Comparable scores on domain-specific legal summarization vs. GPT-4"** | **Vendor's "Legal-Sum" metric: 500 vendor-held (doc, ref-summary) pairs, GPT-4-judged** | **91.4 vs 92.1 (-0.7); 91.4 vs Llama-3-70B 90.8 (+0.6)** | **GPT-4 is the judge; corpus is proprietary; training data was GPT-4-rewritten** |

Two sub-claims that the whitepaper's own tables undermine - worth naming
because they constrain what the headline can mean:

| # | Sub-claim surfaced by the tables                           | What the table shows                                          |
|---|------------------------------------------------------------|---------------------------------------------------------------|
| 5 | ModelZip-7B is NOT comparable on reasoning                 | BBH 61.8 vs Llama-3-70B 67.3 (-5.5pp); HumanEval 42.1 vs 50.6 (-8.5pp) |
| 6 | LegalBench-small gap is small, LegalBench-full unreported   | LegalBench-small 73.9 vs 74.8 (-0.9pp); "LegalBench-small" is one of four benchmarks the training-refinement pipeline optimized against |

**The claim that actually matters for your decision is #4.** MMLU, BBH and
HumanEval are proxies at best for a legal-summarization pipeline. The
inference-cost claim (#2) is a hardware fact, not a model-quality fact. The
training-cost claim (#3) is irrelevant unless you plan to retrain. **Legal-Sum
is where the pitch lives, and Legal-Sum is where the backwalk goes.**

---

## 2. Trace to the evaluation harness

For each number, the instrument that produced it:

| Number | Instrument | Independent of training signal? |
|--------|-----------|---------------------------------|
| MMLU 78.2 | Standard MMLU 5-shot | **No.** Training included (a) 180k GPT-4-rewritten pairs from MMLU's auxiliary train/validation splits and (b) a "benchmark-aware refinement pipeline" that *explicitly scored training candidates against MMLU* |
| BBH 61.8 | Standard BBH 3-shot | **No.** BBH named in the refinement pipeline's target set |
| HumanEval 42.1 | Standard HumanEval pass@1 | **No.** HumanEval named in the refinement pipeline's target set |
| LegalBench-small 73.9 | A subset of LegalBench (size and task composition not specified) | **No.** LegalBench-small named in the refinement pipeline's target set |
| **Legal-Sum 91.4** | **500 (long document, reference summary) pairs from a proprietary SEC-filing + case-law corpus, scored by GPT-4 against the vendor's reference summary on a 1-10 rubric (rubric not published)** | **No** - multiple layers (see Section 3) |
| Inference tok/sec | H100 throughput at bf16, batch and decoding settings unspecified | Yes (hardware fact) |

Where the measurement touches ground truth: nowhere in the Legal-Sum
pipeline. Every signal passes through a layer the vendor controls - the
corpus choice, the reference-summary provenance, the rubric design, the
judge choice, the stylistic shape of the training data. Where it touches
a proxy that was in the training loop: everywhere. The headline Legal-Sum
score is a measurement of *how much the model's outputs look like the
vendor's reference summaries, as rated by the same model family (GPT-4)
whose style the training data was rewritten into*.

MMLU, BBH, HumanEval and LegalBench-small are not independent of the
training signal either. The whitepaper is unusually explicit about this:
training candidates were *filtered* against those exact benchmarks. The
numbers in those columns are not out-of-distribution evaluations - they
are near-training-distribution evaluations, by construction.

---

## 3. What each claim rests on - load-bearing assumptions

### A. Judge-dependence (distributional)

**The specifics.** Legal-Sum is scored by GPT-4. ModelZip-7B's training
set includes a 180k-pair subset lightly rewritten by GPT-4 for "stylistic
diversity," and a general pipeline that filters candidates through
vendor-held quality thresholds whose relationship to GPT-4-as-judge is
not stated. If GPT-4 preferentially rates outputs that resemble its own
output distribution, a model trained on GPT-4-rewritten data will score
higher under GPT-4-as-judge than a model (Llama-3-70B) not so trained -
independent of actual summarization quality. The whitepaper's 91.4 vs
90.8 gap (ModelZip-7B over Llama-3-70B) is a 0.6-rubric-point gap on a
10-point scale. A judge-affinity effect of that size is empirically
common in the LLM-as-judge literature (Zheng et al. 2023; Wang et al.
2023).

**Counterfactual.** If Legal-Sum scores are judge-dependent, then re-scoring
the same model outputs with Claude-3.5-Sonnet, Llama-3-70B-as-judge, or
human raters will narrow or reverse the ModelZip-7B advantage over
Llama-3-70B. The "matches GPT-4" framing stops holding.

### B. Reference-summary circularity (definitional)

**The specifics.** Legal-Sum scores outputs *against vendor-held reference
summaries*. The whitepaper does not say who wrote those references.
Three possibilities, with very different implications:
1. Human legal experts wrote them. Score is a reference-fidelity measure.
2. GPT-4 wrote them. Score measures how closely ModelZip-7B replicates
   GPT-4-style summaries of these documents - tautological given the
   training pipeline.
3. The vendor's own earlier models wrote and then humans edited them.
   Score measures a mix, direction unknown.

None of the three is faithfulness-to-source. "Does this summary say true
things about this document?" is not a question Legal-Sum asks. A
hallucinated claim that happens to echo the reference wins; a correct
claim that diverges from the reference loses.

**Counterfactual.** If the headline score is doing work by rewarding
reference-fidelity rather than source-faithfulness, a source-grounded
faithfulness audit (per-claim entailment against the input document)
will show ModelZip-7B producing a materially higher rate of unsupported
claims than Llama-3-70B, because the compressed model has less capacity
to recover from reference-style summary templates when the source
doesn't support them.

### C. Corpus transfer (sampling)

**The specifics.** The Legal-Sum corpus is "a proprietary corpus of SEC
filings and case law." That is not the same distribution as *your team's*
legal-summarization workload - unless your workload is SEC filings and
case law. The whitepaper offers a 500-example test set drawn from a
specific genre. Legal-summarization pipelines in practice see contracts,
briefs, memoranda, patents, due-diligence packets, discovery sets, and
in-house compliance docs; each has its own structural conventions and
stylistic registers. A model tuned on SEC-filing summarization is not,
by that fact, tuned on contract redlining.

The whitepaper flags this honestly ("we encourage independent
evaluation"). The backwalk flags it here because it is load-bearing:
Legal-Sum 91.4 is a number about a specific 500-document distribution,
not about your 500 documents.

**Counterfactual.** If vendor-corpus performance doesn't transfer, running
the same evaluation protocol on 50-100 documents sampled from your
actual pipeline will show the ModelZip-7B / Llama-3-70B gap widen in
Llama's favor on your distribution, even using the vendor's own (GPT-4)
judge.

### D. Benchmark-targeted training (definitional + sampling, chained)

**The specifics.** The whitepaper is candid that the training pipeline
scored candidate instructions against MMLU, BBH, HumanEval and
LegalBench-small. This is not test-set contamination in the strict sense
(the pipeline scored training candidates, not test answers), but it is
*benchmark-shaped training*: the model was selected for performance on
distributional properties of those benchmark question sets. The claim
that ModelZip-7B "matches Llama-3-70B on MMLU" is partially a
measurement of how much training compute was spent making MMLU-shaped
questions easy, not an estimate of generalization to MMLU-adjacent
reasoning. The 5.5pp BBH gap and 8.5pp HumanEval gap suggest the
benchmark-shaping doesn't carry evenly across reasoning types.

Critically for the decision at hand: "LegalBench-small" was in the
refinement pipeline's target set. The 73.9 vs 74.8 near-tie is an
in-distribution number. Legal-Sum is *also* vendor-controlled, so
there is no column in the whitepaper where legal performance is
measured outside vendor-shaped evaluation.

**Counterfactual.** If benchmark-targeted training doesn't generalize,
performance on *full* LegalBench reasoning tasks (not "LegalBench-small"),
on structurally different legal reasoning tasks (contract NLI, rule
application, interpretation), and on your own workload will show a
larger ModelZip-7B / Llama-3-70B gap than the LegalBench-small
near-tie suggests.

### E. Long-context robustness (operational)

**The specifics.** The whitepaper names 8k native context, extended to
32k via YaRN. Legal documents routinely exceed 32k tokens (a merger
agreement, a 10-K, a lengthy brief). YaRN extension is known to degrade
long-range recall, especially past 2x the native context, and
especially for information in the back half of the extended window.
Neither the whitepaper nor the Legal-Sum harness states the token
length distribution of the 500 evaluation documents - if they are all
under 8k, the 32k capability is untested by the headline number.

**Counterfactual.** If ModelZip-7B's YaRN-extended context is weak past
~16k tokens, needle-in-haystack recall and summary faithfulness on
long documents (16k-32k) will degrade sharply, and the real-world
summarization capability will be bounded by document length regardless
of Legal-Sum score.

### F. Reasoning-capacity floor (operational / scoping)

**The specifics.** BBH and HumanEval both show meaningful ModelZip-7B
gaps vs Llama-3-70B. Summarization of legal documents is not pure
summarization - a usable legal summary distinguishes operative clauses
from boilerplate, identifies parties and effective dates, flags
conditional obligations, and preserves limitations of liability. These
are reasoning tasks dressed as summarization. If reasoning capacity
drops with model size (and the whitepaper's own BBH column confirms it
does), the legal-summary quality *as measured by legally-trained
humans* may not track Legal-Sum.

**Counterfactual.** If the reasoning floor matters, blind pairwise
preference judgments by a lawyer on your own corpus will prefer
Llama-3-70B summaries, even when the Legal-Sum / GPT-4 judge prefers
ModelZip-7B.

---

## 4. Code vs. paper

No training code is released. The whitepaper does release "our
evaluation framework" (the 500-pair Legal-Sum harness); the specifics
of the released artifact aren't reproduced here. If you request it
from the vendor before probing, check:

- **GPT-4 model version pinned?** `gpt-4` is not a fixed model; `gpt-4-turbo-2024-04-09`, `gpt-4o-2024-08-06` etc. score differently as judges. If the version floats, the 91.4 number floats too.
- **Rubric prompt released verbatim?** The 1-10 rubric's prompt determines what GPT-4 rewards. "Faithfulness" vs. "coverage" vs. "stylistic quality" each produce different rankings.
- **Reference-summary provenance documented in the release?** (See Section 3.B.)
- **Decoding settings for the candidate models' generations?** Temperature, top-p, max tokens, repetition penalty all shift summary quality.
- **Token-length distribution of the 500 documents?** Determines whether 32k YaRN is exercised.
- **Pairing / seed / order handling?** Does GPT-4 see ModelZip's and Llama's summaries in a known order? Judge-order bias is ~5pp in some settings.

If the released harness answers these, the reproducibility check (below)
is clean. If it doesn't, Probe 1 should fix defensible values and
report them.

---

## 5. Probes

Ordered cheapest-and-most-cutting first. The compute column is
wall-clock on **M3 Max, 128GB unified memory**, using `llama.cpp` /
MLX for local inference. Llama-3-70B is assumed loaded at Q5_K_M (~48GB)
or Q4_K_M (~40GB) to leave headroom for KV cache; ModelZip-7B is
assumed bf16 (~14GB) or fp16. API-side judging uses OpenAI and
Anthropic APIs; dollar estimates are rough and assume current public
rates. Hardware caveat: on MPS, generation is roughly 3-10x slower
than an H100, so probes that would be minutes on an H100 can be hours
here.

### Probe 1 · Judge triangulation on the released Legal-Sum harness (~5-7h wall-clock, ~$60-$120 API)

**Hypothesis.** The 91.4 vs 90.8 ModelZip-vs-Llama-3-70B Legal-Sum
advantage is a judge-affinity artifact of GPT-4 preferring outputs
stylistically close to its own training/output distribution. Under
Claude-3.5-Sonnet as judge, the ModelZip-7B advantage over Llama-3-70B
will shrink by at least 50% or invert. Under Llama-3-70B as judge (self-
judging; worth including for the asymmetric signal), Llama-3-70B will
show a >=1.0 rubric-point preference for itself. Blind pairwise judging
without a reference (adversarial condition, GPT-4-judge) will narrow
to within 5pp of 50/50.

**Protocol.**
1. Pull the released Legal-Sum harness (500 pairs).
2. Subsample to 150 documents, stratified by token length if the harness
   exposes it (else uniform).
3. Generate summaries with ModelZip-7B (bf16 or fp16, temp=0, max_tokens
   = min(1024, source_length/2)) and Llama-3-70B-Instruct (Q5_K_M, same
   decoding).
4. Score each (model, document) summary with three judges:
   - GPT-4 (version-pinned; reproduces the vendor's method)
   - Claude-3.5-Sonnet
   - Llama-3-70B-Instruct (local, same quant as the candidate)
   Use the vendor's rubric prompt verbatim if released; otherwise a
   fixed rubric covering coverage, accuracy, and faithfulness, logged
   in the artifact.
5. Additionally: pairwise no-reference judging, order-randomized, with
   both GPT-4 and Claude as judges, on the same 150 documents.
6. Report per-judge mean Legal-Sum-equivalent scores, pairwise win rates,
   and Spearman rank correlation between judges.

**Falsification.**
- **Confirms the judge-dependence reading.** If the Claude-judged
  ModelZip-vs-Llama-3-70B gap is below +0.3 rubric points (vs the
  vendor's +0.6), OR the gap inverts (Llama-3-70B wins), OR pairwise
  no-reference judging under either judge sits in [45%, 55%] for
  ModelZip-7B.
- **Falsifies.** If Claude-judged gap is within +/-20% of the GPT-4-judged
  gap (0.48-0.72 rubric points in Llama's or ModelZip's favor
  consistently) AND pairwise no-reference judging shows ModelZip-7B
  winning in >=58% of comparisons under both judges, the headline is
  judge-robust.
- **Inconclusive.** Anything in between - report as partial
  judge-dependence; the vendor's claim holds for GPT-4-centric
  pipelines but not necessarily beyond.

**Compute.**
- Llama-3-70B Q5 inference: ~10 tok/sec x 150 docs x ~1000 output tokens = ~4.2h.
- ModelZip-7B bf16: ~60 tok/sec x 150 docs x ~1000 tokens = ~42 min.
- Judge calls via API: 150 x 2 candidates x 3 judges = 900 scoring calls + 150 x 2 pairwise x 2 judges = 600 pairwise calls. Elapsed: <1h; cost: ~$60-$120.
- **Total: ~5.5-7h wall-clock, ~$60-$120.**

### Probe 2 · Source-faithfulness audit (~3-4h wall-clock, ~$40 API)

**Hypothesis.** Legal-Sum measures reference-fidelity, not source-faithfulness.
ModelZip-7B, having been trained on reference-styled summaries, will
produce a higher per-claim unsupported-claim rate than Llama-3-70B on
the same documents. Specifically: ModelZip-7B's unsupported-claim rate
will be at least 1.4x Llama-3-70B's.

**Protocol.**
1. Reuse the 150 (document, ModelZip-summary) and 150 (document,
   Llama-summary) pairs generated in Probe 1.
2. For each summary, split into atomic claims (one assertion per line)
   using Claude-3.5-Sonnet with a fixed decomposition prompt.
3. For each (atomic-claim, source-document) pair, ask Claude-3.5-Sonnet
   (not GPT-4 - avoid overlap with the vendor's judge) to classify
   support as: SUPPORTED / PARTIALLY_SUPPORTED / UNSUPPORTED /
   CONTRADICTED, with a one-sentence rationale.
4. Score a stratified sample (30 claims, 10 per class) by hand to
   calibrate the Claude labels; report labeling agreement.
5. Report: (a) mean unsupported-claim rate per model; (b) rate of
   CONTRADICTED claims per model (high-salience errors); (c)
   per-document scatter of (Legal-Sum score, unsupported-claim rate)
   correlation - is higher Legal-Sum associated with better or worse
   faithfulness?

**Falsification.**
- **Confirms.** ModelZip-7B's unsupported-claim rate is >=1.4x Llama-3-70B's,
  AND the CONTRADICTED rate is >=1.5x higher for ModelZip-7B. This
  means Legal-Sum rewards a model that hallucinates more, as measured
  on the vendor's own documents.
- **Falsifies.** Both models have unsupported-claim rates within 20% of
  each other, AND CONTRADICTED rates within 2 claims per 100. The
  reference-fidelity / source-faithfulness distinction isn't doing
  measurable work here.
- **Inconclusive.** ModelZip-7B has higher unsupported rate but lower
  CONTRADICTED rate (or vice versa) - the models fail differently;
  decide separately which failure mode your legal pipeline tolerates.

**Compute.**
- Reuses Probe 1 summaries (no new generation).
- Claim decomposition: 300 summaries x ~15 claims = ~4500 claims; one
  API call per summary = 300 calls.
- Support classification: 4500 x 1 call each via Claude API.
- Hand calibration: ~1h human-in-the-loop (not compute).
- **Total: ~3-4h wall-clock, ~$40 API.**

### Probe 3 · Your-corpus transfer (~2h compute + 1 lawyer-day, ~$30 API)

**Hypothesis.** The 91.4 Legal-Sum number does not transfer to your
team's actual document distribution. Specifically: under the same GPT-4
judge used by the vendor, ModelZip-7B's advantage over Llama-3-70B on
your documents will either disappear (within +/-0.3 rubric points) or
invert. Under lawyer pairwise preference, Llama-3-70B will be preferred
on 55-65% of document pairs.

**Protocol.**
1. Assemble 50 representative documents from your team's actual
   pipeline. Avoid cherry-picking in either direction - stratify by
   document class (contracts / briefs / filings / memos / whatever
   your mix is) and length.
2. If your pipeline has existing "gold" reference summaries, use them.
   If not, Probe 3 is pairwise-only (no absolute Legal-Sum-style score).
3. Generate summaries with ModelZip-7B and Llama-3-70B at matched
   decoding (same as Probe 1).
4. Machine judges: GPT-4 and Claude-3.5-Sonnet, same rubric as Probe 1.
5. Human judges: 2-3 internal lawyers do blind pairwise preference
   on all 50 documents, with order randomized. Record per-judge
   preferences and inter-rater agreement.

**Falsification.**
- **Confirms the corpus-transfer concern.** ModelZip-7B's GPT-4-judged
  advantage disappears on your corpus (within +/-0.3 rubric points of
  Llama-3-70B) OR lawyers prefer Llama-3-70B at >=55% rate with inter-
  rater agreement kappa >= 0.4.
- **Falsifies.** ModelZip-7B maintains >=+0.4 rubric-point GPT-4-judged
  advantage on your corpus AND lawyers are indifferent (45-55%) or
  prefer ModelZip-7B.
- **Inconclusive.** Judges and lawyers disagree, OR lawyer inter-rater
  agreement is below kappa = 0.2 (your corpus is too heterogeneous for a
  single preference signal).

**Compute.**
- Generation: ~1.5h local inference total.
- Judging: ~$30 API, <1h.
- Lawyer time: ~1 day of real human time, out-of-band of the 20h
  compute budget. If no lawyer is available this week, run the
  machine-judge half and defer the human half.
- **Total: ~2h compute + 1 lawyer-day (parallel).**

### Probe 4 · Long-context needle recall (~6-8h wall-clock)

**Hypothesis.** ModelZip-7B's YaRN-extended 32k context degrades
sharply past ~16k tokens. Specifically: needle-in-haystack recall at
24k-32k will be below 60% for ModelZip-7B, while Llama-3-70B (native
8k; truncate longer docs) will maintain >=80% recall within its range
and, if run at matched Q4-extended 32k, hold >=75% at 24k.

**Protocol.**
1. Build (or adapt from `niah` / `RULER`) 40 synthetic long-document
   needle probes at four length buckets: 4k, 12k, 20k, 28k tokens
   (close to but not exceeding 32k to keep Llama's extended context
   usable at Q4). Each probe inserts a specific clause ("The effective
   date of this amendment is March 14, 2024") at a known relative
   position (25% / 50% / 75% / 90%).
2. Ask each model to answer a question requiring the needle, OR to
   summarize the document in a way that would include the needle.
3. Score: did the output contain the correct needle fact, verbatim or
   paraphrased? Binary per probe.

**Falsification.**
- **Confirms the degradation reading.** ModelZip-7B recall at 20k-28k
  drops below 60% AND Llama-3-70B at matched length holds >=75%, with
  the gap widening at the 75% / 90% needle positions.
- **Falsifies.** ModelZip-7B maintains >=85% recall across all four
  length buckets and all four positions.
- **Inconclusive.** Both models degrade similarly, OR ModelZip-7B
  degrades only at the 90% position (ends of long documents) - flag
  as a constraint on document type, not a general failure.

**Compute.**
- Longest ModelZip-7B runs (28k context) at ~15 tok/sec: ~3h.
- Llama-3-70B Q4 at 28k context on 128GB Mac: ~2-4 tok/sec, memory-bound;
  ~4-5h. Running at matched quant and length may require Q4 instead of
  Q5 to fit the KV cache for 28k; note this in the artifact.
- **Total: ~6-8h wall-clock, no API.**

**Run this probe only if your legal workload actually includes
documents in the 12k-32k token range.** If your pipeline tops out at
4k-8k, skip this probe and reclaim the compute for Probe 5.

### Probe 5 · Reasoning regression on full LegalBench (~8-12h wall-clock, ~$20 API)

**Hypothesis.** The LegalBench-small 73.9 vs 74.8 near-tie is a
near-in-distribution effect of training-refinement-pipeline shaping.
On the reasoning-heavy LegalBench subtasks *not* in "LegalBench-small"
(contract NLI, rule application, interpretation), ModelZip-7B will
lag Llama-3-70B by >=5pp, roughly tracking the BBH gap (5.5pp). The
"matches on legal benchmarks" framing holds only on the subset the
vendor selected.

**Protocol.**
1. Identify LegalBench-small's composition from the released harness.
   Then identify the complement: reasoning-heavy tasks in full
   LegalBench that are not in LegalBench-small. Target ~20 tasks.
2. Evaluate ModelZip-7B and Llama-3-70B zero-shot and 5-shot, 50
   examples per task.
3. Where published Llama-3-70B numbers exist, use them as a
   reproducibility anchor; expect your Q5 numbers to be within
   ~1-2pp of fp16-reported.
4. Report per-task accuracy, mean across tasks, and the two-model gap.

**Falsification.**
- **Confirms the benchmark-shaping reading.** Full-LegalBench gap
  (Llama-3-70B minus ModelZip-7B) is >=5pp on at least 60% of tasks.
- **Falsifies.** Gap is <2pp mean, OR ModelZip-7B wins on >=50% of
  tasks.
- **Inconclusive.** Gap is 2-5pp mean - some capability tax, but not
  decision-flipping on its own.

**Compute.**
- 20 tasks x 50 examples x 2 shots (zero + 5) x 2 models = 4000 inference runs.
- ModelZip-7B: ~1-2h total.
- Llama-3-70B Q5: ~6-10h total.
- If Llama numbers are on the LegalBench leaderboard for recent
  versions, substitute to save compute. Note the version drift.
- **Total: ~8-12h wall-clock, ~$20 API if using any judge for
  free-form tasks.**

### Reproducibility check (not a probe) · Reproduce the vendor's 91.4

Before running Probe 1, run the released Legal-Sum harness as-shipped
to confirm the 91.4 number reproduces within +/-1 point. If it doesn't,
you have a bigger problem than any of the probes above - the vendor's
own harness doesn't repro on your setup - and the backwalk pauses
until that's sorted. Allocate ~2h for this; it's mostly Llama-3-70B
generation time, since you'd need to run both models to reproduce
the comparative number.

---

## 6. Probe ordering

| Rank | Probe | Cutting power | Cost (M3 Max) | First-run priority |
|------|-------|---------------|---------------|---------------------|
| 0    | Reproducibility check (repro 91.4) | N/A - a gate, not a probe | ~2h | Yes, before any probe |
| 1    | Probe 1 · Judge triangulation | **High** - collapses or confirms the Legal-Sum headline | ~5.5-7h + ~$60-$120 | **Yes** |
| 2    | Probe 2 · Source-faithfulness | High - tests a dimension Legal-Sum omits | ~3-4h + ~$40 (reuses Probe 1 outputs) | Yes, if Probe 1 confirms or is inconclusive |
| 3    | Probe 3 · Your-corpus transfer | **Highest for your specific decision**, but has a lawyer-dependent half | ~2h + 1 lawyer-day | Yes, start lawyer scheduling now |
| 4    | Probe 4 · Long-context needle | Medium-High (conditional on your doc lengths) | ~6-8h | Only if your pipeline sees 12k+ token docs |
| 5    | Probe 5 · Full LegalBench | Medium (tests capability tax on legal reasoning) | ~8-12h | If time remains after 1-3 |

**20-hour budget allocation suggestion.** Reproducibility (2h) + Probe 1
(7h) + Probe 2 (4h) + Probe 3 compute half (2h) = ~15h. Leaves ~5h
for either Probe 4 or a focused subset of Probe 5. The lawyer-pairing
half of Probe 3 runs in parallel calendar time but outside the compute
window.

**One-sentence rationale.** The cheapest probe (Judge triangulation) is
also the one that most directly attacks the headline Legal-Sum number;
if the 0.6-point advantage over Llama-3-70B is judge-dependent, every
other number in the whitepaper is reframed. Probe 2 piggybacks on
Probe 1's generated summaries for near-zero marginal cost and
surfaces the faithfulness dimension the vendor's metric doesn't
measure. Probe 3 is where the decision actually lands - your corpus
is not SEC filings - but it needs a lawyer, so start the human
scheduling immediately rather than waiting for compute probes to
finish.

---

## 7. Relevance to downstream decisions

For tomorrow's meeting: the whitepaper is empirically suggestive but
structurally vendor-controlled at every layer of the headline claim.
Three framings an engineering leadership conversation can hold:

1. **"The 91.4 number is a measurement of ModelZip-7B's agreement with
   GPT-4-styled reference summaries on a vendor-selected 500-document
   corpus."** That sentence is a fair restatement of what Legal-Sum
   literally measures. Whether that construct correlates with your
   pipeline's quality is Probe 3's question.
2. **"The 11x inference speedup and the Mac-deployable footprint are
   independent of the Legal-Sum claim and robust on their own."** If
   your current pipeline is cost- or latency-bound, those are
   real wins regardless of the quality comparison. Separate them in
   the conversation.
3. **"Running Probes 1-3 inside your 20-hour window costs under $200
   of API and produces a decision-grade signal."** That is a
   substantially smaller commitment than a pilot deployment and
   closes most of what the whitepaper leaves open.

What *not* to say: that the whitepaper is misleading, that the vendor
is being dishonest, or that ModelZip-7B is or isn't the right choice.
None of those is supported by the backwalk. The backwalk supports:
the headline rests on vendor-controlled measurement; here is the
cheapest thing you can run to find out whether the claim holds in
your setting; here is what each result would mean.

---

## 8. What this is not

- **Not a verdict** on ModelZip-7B. The model may be excellent for this
  use case. The probes decide.
- **Not a code review.** Training code isn't released; the eval harness
  is. Section 4 lists what to check in the harness if you request it
  before probing.
- **Not an accusation of contamination.** Benchmark-aware training is
  explicitly disclosed. The backwalk re-reads what that disclosure
  means for the headline numbers.
- **Not a reproduction.** Probe 0 is the reproducibility check; this
  artifact doesn't claim the 91.4 number does or doesn't reproduce.
- **Not advice to keep Llama-3-70B.** The incumbent has its own
  unprobed assumptions - a serious comparison runs Probes 1-3 on both
  models' outputs on your corpus. The choice "which model" is downstream
  of this document.

---

## 9. Key references to follow

1. **Zheng et al., "Judging LLM-as-a-Judge with MT-Bench and Chatbot
   Arena" (NeurIPS 2023).** Establishes the magnitude and structure of
   LLM-as-judge biases. Relevant to Probe 1's falsification margin
   (why +/-20% is the right size, not 5%).
2. **Wang et al., "Large Language Models are not Fair Evaluators" (ACL
   2023).** Position bias, verbosity bias, self-enhancement bias in
   LLM judges - the specific affinity effect this backwalk's Probe 1
   targets.
3. **Zhang et al., "Siren's Song in the AI Ocean: A Survey on
   Hallucination in Large Language Models" (2023), and recent
   SummaC / QuestEval work on faithfulness scoring.** Methodological
   grounding for Probe 2's per-claim entailment approach.
4. **Peng et al., "YaRN: Efficient Context Window Extension of Large
   Language Models" (ICLR 2024), and the RULER long-context benchmark
   (Hsieh et al. 2024).** Necessary for interpreting Probe 4; RULER
   provides a stronger protocol than classic needle-in-haystack.
5. **The LegalBench paper (Guha et al. 2023).** Full task composition
   and reasoning-task breakdown; needed to design Probe 5's complement
   set.

---

**Session note.** Source whitepaper at
`/home/user/skills-work/backwalk/evals/small-model-benchmark-claim/files/modelzip_whitepaper.md`.
This backwalk lives at
`/home/user/skills-work/backwalk-workspace/iteration-1/small-model-benchmark-claim/with_skill/outputs/analysis.md`.
Follow-up artifacts planned: after Probe 1, re-rank remaining probes
based on whether judge-dependence confirmed; after Probe 3, update
Section 7 with the corpus-transfer result.
