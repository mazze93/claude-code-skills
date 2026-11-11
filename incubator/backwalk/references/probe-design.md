# Probe Design

A probe is an empirical test with four committed parts: hypothesis,
protocol, falsification criterion, compute estimate. Each part must be
written *before* the probe runs. If any is missing, the probe isn't
designed yet — it's a vague wish.

## Hypothesis

A prediction specific enough to be wrong.

**Bad hypothesis.**
> I wonder what happens if we score the outputs with a different classifier.

**Good hypothesis.**
> IF-Guide's headline 10× EMT reduction is a joint function of (method,
> classifier). If measured with a classifier outside Detoxify's lineage,
> the effect size will drop by at least 40% (reducing the 10× to under
> 6×). Specifically: Perspective API, Llama Guard 3, and OpenAI
> moderation will each show smaller reductions than Detoxify, and the
> three will agree with each other more than any agrees with Detoxify.

The second commits to a direction and a magnitude. The first doesn't
commit to anything, so no result would surprise it.

**Test for a hypothesis.** Can someone read it and write down, in
advance, the three outcomes that would confirm it, falsify it, or
leave it uncertain? If no, rewrite.

## Protocol

Exactly what will be run. Not "we'll evaluate with multiple classifiers"
— specify:

- Which classifiers, by version.
- Which input prompts, by index or by name.
- Which completions, how generated (decoding settings, temperature,
  top-p, max tokens).
- How many samples per prompt.
- Which metrics are computed (EMT, TP, AUC, pass@k).
- What constitutes a "pass" per metric.
- Which seed, if applicable.

**Signature of a good protocol.** Someone else could run it from the
protocol alone and get numbers comparable to yours. If re-running
would require asking you a question, the protocol has a hole.

**Signature of a bad protocol.** Hand-waves at "and we'll check the
results" without saying how.

## Falsification criterion

The threshold that would change your mind. Chosen before the probe
runs, not after.

**The rule.** Write the criterion so that any specific numerical
outcome either falsifies, confirms, or inconclusively leaves your
hypothesis standing. No outcome should be unassignable.

**Bad criterion.**
> If the effect is smaller under other classifiers, the circularity is
> confirmed.

(How much smaller? 10%? 50%? 99%? What if it's smaller for two but
larger for one?)

**Good criterion.**
> **Confirms.** If the geometric mean of EMT reductions across
> Perspective, Llama Guard 3, and OpenAI moderation is below 3×
> (vs. Detoxify's ~5×), and no single alternative classifier shows
> reduction above 4×, the classifier-dependence is substantial.
> **Falsifies.** If at least two of the three alternative classifiers
> show reduction within ±20% of Detoxify's measurement, the effect
> is classifier-robust and the circularity concern is overstated.
> **Inconclusive.** Anything in between — report as "partial
> classifier-dependence" without a strong claim.

The confirming and falsifying regions should be of comparable size.
If "confirmation" is "any smaller number" and "falsification" is
"exactly the same number," the probe is rigged.

## Compute estimate

Hours (or days) on the user's actual hardware.

**Includes.**
- Model loading time.
- Inference time per sample × sample count.
- Any training/fine-tuning compute.
- Any score-aggregation / re-scoring.
- Human-in-the-loop time if the probe has one.

**Excludes.**
- Thinking time.
- Writing the report.
- Debugging unrelated to the probe.

**Conversion.** Papers report H100 hours. Convert to:
- **M-series Mac (MPS):** roughly 3-10× slower for generation,
  substantially slower for training, depending on op kernel coverage.
- **Older NVIDIA (3090/4090):** roughly 1.5-3× slower than H100.
- **CPU:** generally infeasible for anything beyond 1B param inference
  on small batches.

**Example.** Paper reports "EK-FAC on 1B tokens: 7.5 hours on H100 with
Pythia-160M." On an M5 Pro with MPS, expect 30-100 hours. On a 4090,
expect 15-25 hours. On CPU: not feasible.

If the honest estimate on the user's hardware is "weeks," the probe
needs redesign — subsample, use released checkpoints, or move to a
smaller proxy. A probe that will never actually run isn't a probe.

## Probe ranking

After designing all probes, rank by (cutting power) / (cost). Cutting
power = fraction of the claim's edifice that collapses if the probe
falsifies. Cost = compute estimate.

**High cutting power.** Probes that target an assumption underneath
the headline claim. If the assumption fails, the headline doesn't
recover with a smaller qualifier — it becomes false.

**Low cutting power.** Probes that target an ancillary claim. The
headline survives.

**High cost.** Full retraining. Multi-week compute. Custom benchmarks.
**Low cost.** Inference-only on released checkpoints. Reusing paper's
own data splits. Classifier substitution.

The first probe should be the cheapest-and-most-cutting. The user who
has time for one probe should get the one that most changes the
picture.

## Probes that don't fit this template

Not every empirical question is a probe. Some things are:

- **Exploratory sweeps.** "What does the activation space look like
  across layers?" — useful, but not a probe. Frame separately.
- **Reproducibility checks.** "Can we rerun the paper's setup and get
  their numbers?" — valuable, but before probing, not instead of it.
- **Qualitative analysis.** "What do the suppressed tokens actually
  look like?" — again, useful context but not a probe unless tied to
  a hypothesis with a falsification criterion.

Mark these "exploratory" or "reproducibility" and keep the probe set
clean. Mixing explorations into probe rankings makes the artifact
harder to act on.
