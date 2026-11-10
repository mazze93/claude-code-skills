# ModelZip-7B as a Llama-3-70B Replacement for Legal Summarization

**Status:** Pre-decision analysis · For engineering leadership review
**Author:** Research
**Date:** 2026-11-07
**Source under review:** StackMeadow AI, *ModelZip-7B whitepaper* v1.2.0 (2026-10-28)
**Bench available:** M3 Max, 128 GB unified memory · **Compute budget:** ~20 hours this week

---

## 1. TL;DR for the meeting

The whitepaper makes one decision-relevant claim and several claims that look supportive but aren't. The decision-relevant one — *"ModelZip-7B matches Llama-3-70B on legal summarization"* — is backed **only by the vendor's own, GPT-4-judged, undisclosed-corpus metric**. The MMLU/BBH/HumanEval numbers almost certainly contain **training-set contamination** by the vendor's own description, and the compute-advantage framing is **misleading**: ModelZip-7B is a LoRA fine-tune of Llama-3-8B, not a model trained from scratch, so the "7× less training compute" comparison is apples-to-oranges.

None of the above makes ModelZip-7B useless. A distilled 7B that genuinely holds up on **our** legal documents under **our** fidelity requirements would be a real win — ~11× cheaper per token and small enough to run on-prem. **But the whitepaper does not establish that.** It establishes that someone trained a small model to do well on benchmarks they also designed.

**Recommended ask of leadership:** Do not commit this week. Approve a scoped 20-hour evaluation on our own documents, with the four decision-blocking tests below. If those pass, re-engage the vendor with pointed questions and run a longer pilot. If any of the first two fail, stop.

---

## 2. What is actually being claimed?

The whitepaper rolls several distinct claims into one headline. Separating them is step one:

| # | Claim | Decision-relevance for us |
|---|-------|---------------------------|
| C1 | ModelZip-7B ≈ Llama-3-70B on MMLU (78.2 vs 79.5) | Low — MMLU is not what we do |
| C2 | ModelZip-7B ≈ Llama-3-70B on BBH/HumanEval | Low — not what we do, and here they report ~5–8 point gaps anyway |
| C3 | ModelZip-7B ≈ Llama-3-70B / GPT-4 on legal summarization | **High — this is our use case** |
| C4 | ~11× faster inference (H100 tok/s) | Moderate — directionally true for 7B vs 70B, but H100 numbers don't map to our serving env |
| C5 | ~7× less training compute | Low — misleading, see §4 |
| C6 | Fits 24 GB GPU / 64 GB+ unified-memory Mac | Moderate — operationally useful if C3 holds |
| C7 | 8k context, YaRN-extendable to 32k | **High and under-advertised** — most of our legal source documents exceed this |

Only **C3, C6, C7** should drive this decision. C1, C2, C5 should not be in the room.

---

## 3. The backwards walk: C3 ("matches GPT-4 / Llama-3-70B on legal summarization")

The headline table reports:

```
Legal-Sum metric:  ModelZip-7B 91.4   Llama-3-70B 90.8   GPT-4 92.1
```

For this to be the basis of a production decision, we need to walk the following chain and have every link hold up:

> (Evidence) → (Evidence is sound) → (Evidence is representative of our workload) → (Model behaviour generalises) → (Operational fit)

### 3.1 What the evidence actually is

- 500 (long document, reference summary) pairs.
- Documents drawn from "a proprietary corpus of SEC filings and case law." Not released.
- **Reference summaries: source not stated.** If these were produced by GPT-4, then GPT-4 judging summaries against GPT-4-produced references is circular — it biases the eval toward whoever sounds the most like GPT-4. ModelZip-7B's training pipeline explicitly rewrote data using GPT-4 "for stylistic diversity"; that path is wide open here.
- Judge: GPT-4, 1–10 rubric, mean ×10.
- No confidence intervals. No inter-rater agreement. No comparison against a human gold standard.
- **No faithfulness/hallucination metric** reported — which for legal use is the metric.

What the table actually supports: *a GPT-4-style judge, on documents the vendor chose, finds ModelZip-7B's summaries nearly as pleasing as GPT-4's.* That is a long way from *"will reliably summarise our case filings without inventing a holding or dropping a party."*

### 3.2 The three specific weaknesses to probe

1. **Judge bias.** GPT-4-as-judge is well-documented to favour verbose, GPT-4-styled outputs regardless of factuality. Three models (ModelZip, Llama-3-70B, GPT-4) clustering within 1.3 points on a 100-point scale is more consistent with a rubric ceiling / judge-flattening effect than with the three being genuinely interchangeable.
2. **Corpus mismatch.** "SEC filings and case law" is a huge space. Our workload (describe it in the meeting — 10-Ks? M&A diligence memos? deposition summaries? regulatory correspondence?) may be nothing like the slice the vendor sampled.
3. **Fidelity vs. fluency.** The rubric isn't published. A 1–10 score on "quality" can hide the failure modes we most care about: dropped parties, wrong dates, misattributed quotes, invented statute numbers, swapped $M/$B, hallucinated citations. For a legal summariser these are not stylistic defects; they are liability.

### 3.3 The contamination problem that bleeds into everything

By the vendor's **own description**, the training set contains:

- A "benchmark-aware refinement pipeline that scores candidate instructions against our target downstream benchmarks (MMLU, BBH, HumanEval, LegalBench-small)."
- "A 180k-pair subset derived from MMLU's auxiliary training and validation splits, lightly rewritten by GPT-4."

Training on MMLU validation data and then reporting MMLU scores is the textbook definition of benchmark contamination. This is not a subtle inference; they wrote it in the methodology section. It explains why a LoRA fine-tune of Llama-3-8B (MMLU 68.4) landed at MMLU 78.2 — a ten-point jump from 768 H100-hours of LoRA tuning is otherwise implausible.

This matters for our decision in two ways:

- It directly invalidates the MMLU/BBH/HumanEval columns as *generalization* evidence. They are memorisation or near-memorisation evidence.
- It raises the base rate of "the Legal-Sum numbers were also optimised against." The training pipeline was explicitly designed to score well on target benchmarks. Legal-Sum is one of them, and is the vendor's own.

The right posture is: **until independently verified on data the vendor had no access to, treat the numbers as the floor of overfitting, not the floor of capability.**

---

## 4. Side-walk: the compute claims (C4, C5)

Before anyone uses these as arguments for ModelZip-7B in the meeting:

- **Inference (~11× faster at 310 tok/s vs 28 tok/s on H100).** Directionally true — a 7B model will beat a 70B on the same silicon by roughly the parameter ratio adjusted for memory bandwidth. But (a) 310 tok/s is a batch-1 best case the vendor doesn't qualify; (b) our deployment environment isn't a single H100, so the tok/s number doesn't translate without re-measuring; (c) Llama-3-70B at 28 tok/s batch-1 is on the slow end of published numbers — we should sanity-check against our current pipeline's actual observed rate.
- **Training (~7× less, 768 vs 5,500 H100-hours).** Misleading. ModelZip-7B is LoRA rank-128 on **Llama-3-8B**. The honest comparison is `Llama-3-8B pretrain + 768 LoRA hours` vs `Llama-3-70B pretrain`. Llama-3-8B's pretraining compute is in the hundreds of thousands of H100-hours. The 7× number is not a model-efficiency claim; it's a fine-tune-vs-pretrain accounting trick. This affects whether we believe the vendor's narrative about their distillation process being special — it probably isn't; the heavy lifting was done by Meta.

Neither of these is itself a reason not to evaluate the model. They *are* reasons not to let compute claims carry weight in the decision.

---

## 5. What should we actually test? (20-hour plan on the M3 Max bench)

Design principle: every test should either (a) decide the deal or (b) be cheap enough that it's worth doing in case the earlier tests pass. Tests are ordered so we can stop early on a failure.

### Test 1 — Contamination probe on MMLU variants · ~2 hours · cheap, high-information

**What:** Run ModelZip-7B on MMLU-Redux (de-contaminated MMLU) and MMLU-Pro. Compare its scores to the whitepaper's 78.2.

**Why:** The vendor admitted training on MMLU-adjacent data. If performance craters on MMLU-Redux / MMLU-Pro (e.g. drops below Llama-3-8B's 68.4 baseline on the uncontaminated slice), we have proof that the headline benchmark numbers are artifacts. If the drop is modest, contamination is partial. If there's no drop, we learn something unexpected.

**What it tells us:** *How much to trust anything else the vendor reports.* This is a cheap trust meter. It does not directly bear on legal summarization, but if the model is a benchmark-overfit artifact, the Legal-Sum number almost certainly is too.

**Stop condition:** If ModelZip-7B ≤ Llama-3-8B on MMLU-Redux, we stop and the meeting is short.

### Test 2 — Head-to-head on our own documents, blind, human-judged · ~8 hours · the actual test

**What:** Take 30–50 recent, representative documents from our production pipeline (varied in length, type, and complexity). For each, generate summaries from:

- ModelZip-7B (at bf16 on the M3 Max; via llama.cpp or MLX).
- Our current Llama-3-70B pipeline (the one we'd be replacing).
- Optionally a GPT-4 reference, if budget allows.

Strip metadata. Shuffle. Have 2–3 of our team (ideally including whoever QA's the current pipeline's output) rate each blindly on the **failure modes that matter to us**, not a 1–10 rubric:

| Dimension | Scale | Why |
|---|---|---|
| Faithfulness (does every claim trace to the source?) | pass / minor issue / fail | The single most important axis |
| Factual completeness (are the summary-critical facts present?) | pass / minor / fail | |
| Named-entity fidelity (parties, judges, courts) | counted errors | Easy to score |
| Numeric fidelity (dates, amounts, section numbers) | counted errors | Common hallucination surface |
| Citation fidelity (case names, statutes, docket numbers) | counted errors | Legal-specific, high-cost errors |
| Fluency/usability | 1–5 | Soft but relevant |

**Why:** This is the only test that directly answers the question in front of us. It uses our data, our reviewers, and the failure modes a legal-summarization pipeline actually has to survive. It's judge-independent — no GPT-4 in the loop.

**What it tells us:** Whether ModelZip-7B is production-viable *for us*, independent of any vendor marketing frame.

**Stop condition:** If faithfulness fail rate > Llama-3-70B's by any meaningful margin, or if named-entity/numeric/citation error counts rise, this is a non-starter regardless of fluency.

### Test 3 — Context-length behavior on real document lengths · ~3 hours

**What:** Measure the length distribution of our actual production documents. For documents that exceed 8k tokens (and for those that exceed 32k), compare three strategies:

- ModelZip-7B at 8k context with map-reduce chunking (the realistic deployment).
- ModelZip-7B at 32k via YaRN (per vendor claim).
- Llama-3-70B at its native context on the same document.

Score the same fidelity dimensions as Test 2. Pay special attention to whether facts near the middle/end of long documents drop out of ModelZip's summaries.

**Why:** 10-Ks are routinely 100k+ tokens. Case law records are longer. If 80% of our workload exceeds ModelZip's native window, the cost advantage is partly erased by the orchestration complexity of chunking, and the fidelity story gets worse. YaRN-extended contexts are known to degrade quality — "extendable to 32k" is not the same as "works well at 32k."

**What it tells us:** Whether the deployment architecture becomes materially more complex, and whether fidelity holds at the lengths we actually run.

### Test 4 — Operational fit: throughput and memory on realistic serving · ~2 hours

**What:** On the M3 Max (as a proxy for whatever eventual serving env we'd use, understanding it's not identical), measure:

- Tokens/sec at batch 1 for ModelZip-7B bf16 and for Llama-3-70B (likely Q4 or Q5 quantization at 128 GB; a 70B at bf16 does not fit in 128 GB).
- Time-to-first-token for a long document.
- Peak memory, memory stability over an extended run (does it leak? does unified memory pressure spike?).
- End-to-end cost per document including any chunking/reduce overhead from Test 3.

**Why:** The vendor's "11× faster" number is on H100. Our serving environment isn't an H100. We need our own numbers for the business case.

**What it tells us:** Realistic cost-per-document comparison, which is what leadership will actually need to see.

### Test 5 — Faithfulness stress probes · ~3 hours · if we get this far

**What:** Construct 20–30 adversarial documents designed to tempt hallucinations:

- Documents with similar-looking party names (easy to confuse).
- Documents citing non-existent statutes or with unusual formatting.
- Long documents where key facts appear only in one place (test for coverage).
- Documents with explicitly contradictory statements (test whether the model picks one and asserts it as settled).

Compare ModelZip-7B vs Llama-3-70B on failure rates.

**Why:** Averaged scores hide worst cases. Legal pipelines live or die on worst cases.

**What it tells us:** Tail-risk profile.

### Reserve: ~2 hours

Setup, download, tooling, writing up the comparison.

### Total: ~20 hours

If Test 1 fails, stop (~2 hours used).
If Test 2 fails, stop (~10 hours used).
Everything past Test 2 is only worth running if Tests 1–2 look promising.

---

## 6. Questions for the vendor (ask only if Tests 1–2 pass)

- How were the 500 Legal-Sum reference summaries generated? If GPT-4, the metric is largely a GPT-4-similarity score; we should disregard it.
- What is the Legal-Sum rubric, verbatim? Who wrote it?
- What is the inter-rater agreement between the GPT-4 judge and a legal expert on a sample of Legal-Sum? (If they haven't measured this, that itself is an answer.)
- Can we see faithfulness / hallucination numbers broken out from the 1–10 quality score?
- Was the base Llama-3-8B pretraining compute included in the "7×" comparison? (We know the answer; we want to see them handle the question.)
- What is the exact text of the "permissive commercial license"? Any restrictions on derivative outputs, attribution, re-distribution of fine-tunes, or training-data provenance that we need for legal-domain deployment?
- What is the model's behavior under refusal / safety stress? ("Not safety-aligned; vendors should apply their own alignment stack" is a line we need to price in.)
- Are there any customers already in production for legal summarization? Can we talk to one?

---

## 7. What a positive and a negative look like

**Positive outcome (deploy, or at least extend pilot):**
- Test 1: ModelZip-7B holds within 3–5 points of its whitepaper MMLU number on MMLU-Redux. (Some drop is expected and acceptable; a crater is not.)
- Test 2: Faithfulness, named-entity, numeric, and citation-fidelity scores are statistically indistinguishable from Llama-3-70B on our documents, with no new failure modes.
- Test 3: Either our document-length distribution is within ModelZip's native 8k, or chunking/YaRN holds fidelity well enough for our workload.
- Test 4: Cost-per-document is materially better than the current pipeline in our actual serving env.
- Test 5: No class of document in our workload hits a catastrophic failure mode that 70B avoided.

**Negative outcome (do not deploy):**
- Test 1 shows MMLU-Redux crater → the benchmark numbers are overfit, update priors sharply downward on everything else.
- Test 2 shows higher error rate on named entities, numbers, or citations — these are the error classes with the highest legal and reputational cost.
- Test 3 shows fidelity collapse at our document lengths and chunking adds integration complexity that erases the cost win.
- Any single faithfulness failure mode in Test 5 that would survive to a client.

**Ambiguous outcome (most likely):**
ModelZip-7B is clearly cheaper and clearly faster; it's also clearly a little worse on at least one of faithfulness / long-context / tail documents. Then the decision is a business question, not a technical one: what's the cost of a worse summary vs. the cost per document? Leadership can answer that if we hand them concrete numbers from Tests 2–4. The whitepaper does not let us hand them those numbers; this evaluation plan does.

---

## 8. What to say in the meeting tomorrow

A one-paragraph version if you want to lead with it:

> The vendor's whitepaper makes one claim that matters for our decision — "matches 70B on legal summarization" — and that claim rests entirely on a benchmark the vendor designed, judged by GPT-4, on a corpus we can't see. The headline MMLU and compute numbers are either misleading or evidence of benchmark contamination the vendor describes in their own methodology. None of that rules the model out; small-model distillation for narrow domains is a real trend and the economics would be great if it holds up. But we can't make this call from the whitepaper. I've scoped a 20-hour evaluation on our own documents, with the first two hours designed to kill the deal fast if the benchmark numbers are overfit. I'd like to run it this week and bring real numbers back next cycle.

If asked *why not just trust the Legal-Sum score*: because the same training pipeline that made it score well also trained on validation data for the public benchmarks it's reported on. That's not an inference — it's in their methodology section.

If asked *can the M3 Max even run Llama-3-70B for comparison*: Yes, at Q4 or Q5 quantization (~40–50 GB). Slower than production, but adequate for an A/B eval. The 128 GB headroom is exactly why this bench exists.

---

## 9. Appendix: red flags inventory (for reference, not for the meeting)

Quick index, in rough order of severity:

1. **Direct benchmark contamination, vendor-admitted.** Training set includes "a 180k-pair subset derived from MMLU's auxiliary training and validation splits" and a "benchmark-aware refinement pipeline that scores candidate instructions against our target downstream benchmarks (MMLU, BBH, HumanEval, LegalBench-small)."
2. **Vendor-defined, GPT-4-judged metric is the headline evidence for our use case.** Rubric unpublished, reference-summary provenance undisclosed, corpus proprietary, no inter-rater agreement, no confidence intervals.
3. **Compute-saving claim conflates fine-tune cost with pretrain cost.** "7× less training compute" ignores that the model is a LoRA on Llama-3-8B.
4. **Three models clustering within 1.3/100 on Legal-Sum.** Consistent with rubric ceiling or judge bias, not with the three being functionally equivalent.
5. **Context window understated as a limitation.** 8k native / 32k YaRN is small for legal documents; YaRN-extended context quality is not characterised.
6. **"Not safety-aligned; vendors should apply their own alignment stack."** This is a real integration cost for legal-domain deployment, not a footnote.
7. **No faithfulness, hallucination, citation-accuracy, or numeric-accuracy numbers.** For legal summarization this is the entire ballgame; its absence from a "legal summarization" whitepaper is itself a signal.
8. **Table formatting choice.** Bolding is used selectively in a way that suggests ModelZip-7B leads where it doesn't (e.g. "Our Legal-Sum metric" bolded for ModelZip-7B while GPT-4 scores higher). Minor, but consistent with marketing framing over scientific framing.
