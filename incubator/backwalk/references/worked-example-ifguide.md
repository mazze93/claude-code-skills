# Worked Example: Backwalking IF-Guide

> **Read this first: the example below is the first pass, and review found errors in it.**
> It is kept unchanged because the iteration-1 eval outputs were generated against it.
> What later review of the full artifact caught:
>
> 1. **No public checkpoints.** The probes are costed as "inference-only, reuse released
>    checkpoints." As of 2026-11-10 no IF-Guide checkpoints are published, so those
>    estimates are wrong until the models are reproduced or obtained.
> 2. **A confound in the "gated, not deleted" reading.** EMT = 1.0 under large negative
>    steering is also what degenerate output looks like to the classifier. The claim needs
>    a coherence measurement next to EMT before it holds.
> 3. **Inherited numbers.** The proxy-overlap means were copied from the paper's text;
>    recomputing from the paper's own table gives different values (44.95% and 47.90%,
>    against the reported 44.61% and 47.22%).
> 4. **An overclaim from a pairwise statistic.** "Disagrees with every other proxy" is more
>    than a pairwise overlap coefficient supports.
> 5. **Wrong table and appendix references**, cited from memory of the structure instead
>    of counted.
>
> A backwalk is itself a set of claims. This one needed a second reader. Iteration 2 of the
> skill should turn these five into steps: verify that every artifact a probe depends on
> exists, recompute any number you repeat, and check each citation against the source.

Condensed walkthrough of applying this skill to arXiv:2506.01790
(Coalson, Bae, Carlini, Hong — "IF-Guide: Influence Function-Guided
Detoxification of LLMs," NeurIPS 2025). The full artifact lives at
`mazze93/IF-Guide-toxic-kitty:knowledge/summary_ifguide.md`; this is
the strategic shape, not the full text.

## Step 1 — Claim as stated

The headline: "Up to 10× reduction in explicit toxicity vs. uncensored
baseline; a million-parameter proxy is as effective as a billion-
parameter target for identifying harmful tokens."

Pulled apart:
- Scope: Pythia 160M-1B and Llama-3.2-1B, trained on 1B tokens OWT.
- Metrics: EMT (max toxicity across 25 generations) and TP (any
  generation above threshold 0.5), Detoxify-scored.
- Comparison: vs. undefended base, vs. DPO, vs. RAD, vs. keyword/
  classifier filtering.
- Qualifiers: "up to," "across models," reported on "full prompt set"
  but also on toxic-subset.

Noted: effect size varies by metric and subset. The single-number
"10×" is the maximum over a grid.

## Step 2 — Trace to evaluation harness

- Query gradients: RTP prompts labeled by Detoxify (toxic > 0.75, safe
  < 0.25).
- Output evaluation: Detoxify, threshold 0.5.
- Implicit toxicity evaluation: ToxiGen-RoBERTa (different classifier).
- Fluency: OpenWebText PPL + LAMBADA accuracy.
- Trade-off: Acc / mean(EMT, TP).

Observation: the same instrument (Detoxify, in particular lineage)
labels the training signal and scores the output. Implicit toxicity
uses a different classifier; its effect size is roughly half.

## Step 3 — Load-bearing assumptions found

Four, one per taxonomy category:

**Distributional:** Detoxify-circular evaluation. Query gradients built
from Detoxify-labeled RTP; outputs scored by Detoxify. Shift to
ToxiGen cuts effect size ~2×. The paper reads this as "generalization
to implicit toxicity." It is also partial evidence that the method's
effect size is classifier-dependent.

**Sampling:** Query ∩ Test overlap on RTP. Verified by loading
`data/RTP/{query,test}_indices/{toxic,nontoxic}_indices.npy` and
intersecting: **4,648 records** appear in both the query set (with
one label) and the test set (with another label, since thresholds
differ: 0.75/0.25 for queries, 0.5 for test).

**Operational:** Every ablation knob is at its stability edge. λ=1
works; λ=1.5 collapses to infinite token repetition. L=2% works; L=2.5%
degrades fluency. τ=99 best; 99.5 fails. Narrow joint operating
envelope.

**Measurement interpretation:** Toxicity "direction" is gated, not
deleted. The paper's §6.2 steering experiment shows positive scaling
has no effect on the IF-Guide model (the model is at floor) but
negative scaling drives EMT to 1.0. That the direction *exists*,
computed from the IF-Guide model's own activations via difference-in-
means, is itself evidence the toxic circuit is retained — if the
circuit were deleted, a coherent direction shouldn't be constructible
from the model's activations.

**Proxy claim deconstructed (secondary, in §5.B of the summary):** The
"a 160M proxy works like a 1B proxy" claim is structurally
*substitutability*, not *equivalence*. Overlap Coefficient between
proxies on the 20M-token selection is 0.446 (Appendix Table 10). On a
20M budget, each pair of proxies disagrees on ~11M tokens and agrees
on ~9M. Downstream toxicity reduction is similar across proxies
because many sufficient subsets exist, not because the proxies find
the same tokens.

## Step 4 — Counterfactuals (what would have to be true)

- If Detoxify-circularity is doing significant work: the effect size
  will drop substantially when scored by an independent classifier.
- If sampling overlap matters: rebuilding the method on strictly
  disjoint records will shrink the effect.
- If the operating envelope matters for transfer: applying IF-Guide
  with the paper's hyperparameters to a different corpus will produce
  inconsistent effects.
- If the toxic circuit is gated: LoRA re-toxification will succeed in
  <1k steps on <1k examples; activation steering on the *base* model's
  toxicity direction, transplanted into the IF-Guide model, will
  reactivate toxicity.

## Step 5 — Probes designed

Six probes, from the full artifact:

1. **Classifier triangulation** — score outputs with 4 classifiers,
   measure effect-size variance. Inference-only, ~1 day wall clock.
2. **LoRA re-toxification** — fine-tune rank-8 LoRA on IF-Guide
   checkpoint with 1k toxic examples, measure EMT at steps
   {0, 50, 100, 200, 500, 1000}. Hours on M5 Pro.
3. **Activation reactivation** — reproduce §6.2 with wider scaling
   range, multiple hook points, transplanted directions. Hours.
4. **LDNOOBW + suppression-loss baseline** — fair comparison to word
   filtering by running the paper's suppression loss on a keyword-
   derived mask. ~1-3 days on M5 Pro.
5. **Capability regression** — evaluate IF-Guide vs. base on tasks
   requiring reasoning about norm-violating content (ToxiGen,
   content moderation, legal argument). Inference-only, ~1 day.
6. **Proxy-disagreement forensics** — characterize what the 55%-per-
   pair of disagreeing tokens actually are. Expensive (score artifacts
   are big), bounded version possible.

## Step 6 — Ranked

1. Probe 1 (classifier triangulation) — highest cutting / lowest cost.
   Could collapse the headline if the effect is Detoxify-lineage-bound.
2. Probe 2 (LoRA re-toxification) — tests durability claim, well-known
   attack class, maps to Qi et al. 2024.
3. Probe 5 (capability regression) — tests the "safety without
   capability tax" subclaim; maps to practical use cases.
4. Probe 3 (activation reactivation) — adds mechanism-level evidence
   to Probe 2.
5. Probe 4 (fair baseline) — expensive, tests only ablation
   completeness.
6. Probe 6 (proxy forensics) — most expensive, tests proxy claim
   which was a secondary headline.

## What this backwalk does not claim

- Not "IF-Guide is wrong." The method's reported numbers reproduce
  within its own harness.
- Not "Carlini missed this." The paper's limitations section covers
  some of this; the backwalk extends it.
- Not "don't use IF-Guide." The right use depends on downstream
  evaluation choices.
- Not "these probes will succeed." Probes designed to falsify can
  also confirm. The method may well be as durable as claimed.

## What the backwalk achieved for its author

- An artifact that could be shared with the paper's authors as
  substantive engagement.
- A probe set sized to a fixed six-week window.
- A written record of where the method's story is tight and where it
  depends on classifier choices.

## Shape to repeat

For a new claim:

- Write §Claims first. Just the headlines.
- Then §Load-bearing assumptions. Don't skip to probes before
  identifying what you're probing.
- Probes come third. If you find yourself writing a probe for an
  assumption you didn't articulate, go back to §Assumptions and name it.
- Rank last. The rank changes everything downstream (what to run,
  what to tell the user).
- Include "What this is not." It closes the artifact.
