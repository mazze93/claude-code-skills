# Load-Bearing Assumption Taxonomy

Four kinds of assumption that silently hold a claim up. For each, the
signature, the kind of probe that tests it, and worked examples.

## 1. Distributional

**Signature.** The training-signal classifier/labeler and the evaluation
classifier/labeler share a lineage, a training dataset, a threshold
calibration, or an author team.

**What to look for.**
- Does the paper use the *same* classifier to generate training labels
  and to score outputs? ("Best-case defender" framings are a tell.)
- Does the method use classifier A (lineage X) for training and
  classifier B (also lineage X) for scoring? Lineage can be:
  - Same training data (e.g., both fine-tuned on Jigsaw civil comments).
  - Same architecture (RoBERTa-base variants are not independent).
  - Same author group / lab.
- Does the paper report a smaller effect when a classifier outside the
  lineage is used? The ratio of effects across classifiers is the
  distributional footprint.

**Example (IF-Guide, arXiv:2506.01790).**
- Query gradients labeled by Detoxify (threshold 0.75 / 0.25).
- Outputs scored by Detoxify (threshold 0.5).
- Explicit-toxicity effect size with Detoxify: ~5× EMT reduction.
- Implicit-toxicity effect size with ToxiGen-RoBERTa (different
  classifier, different lineage): 2.2× EMT reduction.
- The ratio (5× / 2.2× ≈ 2.3) is a partial estimate of the distributional
  dependence. The paper frames the drop as "generalization to implicit
  toxicity." It is also a classifier-dependence estimate.

**Probe pattern.** Re-score outputs with N independent classifiers, from
independent lineages. The effect size under each is a column; the ratio
across columns is the distributional dependence.

## 2. Definitional

**Signature.** The metric is a function of a classifier/judge/benchmark
that was in the training loop — not the same examples, but the same
instrument that defines what "correct" means.

**What to look for.**
- Benchmarks whose labels define the construct (e.g., MMLU defines
  "general knowledge" by its question set; a method that is tuned
  against MMLU is tuned against *MMLU-defined* general knowledge, not
  general knowledge in the abstract).
- Judge models that score outputs. If the judge is GPT-4 and the method
  was tuned to produce outputs GPT-4 scores highly, "GPT-4 says it's
  good" is close to a tautology.
- Thresholds. Even with classifier independence, a threshold tuned on
  the test set's score distribution is a form of definitional leak.

**Example (RLHF-style benchmarks).** Many "preference win rate" numbers
are definitional: the preferences the method optimizes over are the
preferences that score it. Reporting a win rate against the preference
function you optimized is reporting an in-sample fit.

**Probe pattern.** Replace the metric's definitional instrument with an
independent one. If "GPT-4 win rate" was the metric, re-score with
Claude or Llama Guard. If a benchmark was the metric, evaluate against
an adversarial subset the benchmark's labels don't cover cleanly.

## 3. Operational

**Signature.** A hyperparameter is at the edge of a stability cliff. The
method works at the reported setting; adjacent settings break it.

**What to look for.**
- Ablation tables. If the paper reports {0.5, 1, 1.5, 2} and 1 is best,
  check whether 1.5 breaks or just underperforms. "Training destabilizes"
  / "model collapses" / "repeats tokens" in the text is a tell.
- The optimal setting at the edge of a range rather than in the middle
  (99th percentile best; 99.5 "too conservative" means 99 is at the
  high end of what works).
- Multiple knobs each at their own cliff. If L is best at 2% and
  destabilizes at 2.5%, λ is best at 1 and destabilizes at 1.5, and
  threshold is best at 99% and fails at 99.5%, the method has a narrow
  joint operating region, which rarely transfers across corpora/models.

**Example (IF-Guide ablations).**
- L (token budget): 2% works, 2.5% degrades fluency.
- λ (penalty): 1 works, 1.5 produces infinite token repetition.
- τ_tox (percentile): 99 best, 99.5 "too conservative."
- Context window w: 1 best, 0 and 2 both lose.
- Every knob at an edge.

**Probe pattern.** Cross the operating envelope. Vary two knobs jointly
and plot the stability region. If the stable region is small, hyper-
parameter transfer to a new corpus will fail.

## 4. Sampling

**Signature.** The query set and the test set share records at the
raw-content level, even when they're labeled as disjoint.

**What to look for.**
- Benchmarks reused for both training-signal and evaluation. If RTP is
  the source of toxic queries *and* the source of eval prompts, check
  the index overlap.
- "Disjoint" claims that only hold under a label×record join, not the
  raw record set. (A record classified "toxic" for queries can reappear
  as "non-toxic" for test under a different threshold.)
- Cross-split threshold placements that create a non-overlapping region
  at the middle of the score distribution — the gap means the two
  splits are drawn from overlapping sources.

**Example (IF-Guide data audit).**
- 19,785 query toxic + 64,327 query non-toxic + 5,000 test toxic + 5,000
  test non-toxic.
- |query ∩ test| = **4,648 records** (verified by loading the .npy files
  and intersecting the index sets).
- The paper claims "test examples are distinct from those in the
  influence computation." The intersection is zero on (label, record)
  pairs but 4,648 on records alone.
- Not a classical train/test leak — the training data is OpenWebText —
  but the *query gradient* that selected tokens is drawn from a pool
  with a 46% raw-content overlap with the eval pool.

**Probe pattern.** Rebuild the method using only the strictly-disjoint
subset (records never appearing in either query label and never appearing
in the test set) and re-evaluate.

## Signatures that are NOT load-bearing assumptions

Don't flag:
- Known limitations the authors name explicitly (they're controlled for
  or acknowledged).
- Compute scope ("only tested up to 12B parameters") — this is a scoping
  issue, not an assumption.
- Benchmark choice when there's no reasonable alternative.
- Reasonable baseline omissions (asking "why didn't they compare to X"
  when X is from last month).

The point is to find the assumptions the paper's story *depends on*
without naming — not to inventory everything the paper could have
done differently.
