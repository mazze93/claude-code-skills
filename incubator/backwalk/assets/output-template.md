# Backwalk: {CLAIM SOURCE}

**Source:** {paper / assessment / pitch / benchmark — link or citation}
**Reviewed:** {YYYY-MM-DD} · backwalk · {register, e.g. "adversarial read"}
**Tag:** `{slug for cross-references}`

> **Note on reading register.** This is an adversarial read: a surface
> for probes, not a verdict. The work being probed may be excellent.
> The point is to know *how* it is excellent, and where that excellence
> depends on choices that might not hold outside the specific harness.

---

## 1. Claims as stated

| Claim                              | Scope / population               | Effect size (reported)       | Qualifier                 |
| ---------------------------------- | -------------------------------- | ---------------------------- | ------------------------- |
| {Headline 1}                       | {which model, which dataset}     | {metric and number}          | {"up to," "on average"}   |
| {Headline 2}                       | {...}                            | {...}                        | {...}                     |

---

## 2. Trace to the evaluation harness

Brief: what classifiers, benchmarks, judges, datasets produce the
numbers above. Where does the measurement touch ground truth? Where
does it touch a proxy that was in the training loop?

---

## 3. What each claim rests on — load-bearing assumptions

### A. {Distributional assumption, named in one line}

The specifics. What is shared between training signal and evaluation.
What would have to be true for this not to matter. How the paper
addresses or doesn't address it.

**Counterfactual:** If {X} is not true, {Y} stops holding.

### B. {Definitional assumption}

(Same shape.)

### C. {Operational assumption}

(Same shape.)

### D. {Sampling assumption}

(Same shape.)

Add more sections only if you've actually identified another load-
bearing assumption. Five is usually a good upper bound; more and the
artifact loses its edge.

---

## 4. Code vs. paper

Skip this section if no code is available. Otherwise:

- Hyperparameter defaults in code that don't match the paper
- Dead code paths (function defaults vs. CLI defaults)
- Undocumented knobs that could change results
- Data splits as they appear on disk vs. as described in the paper
- Checkpoint selection criteria
- Loss function arithmetic (verify the code implements the equation
  the paper states)

For each: what the paper says, what the code does, whether the drift
matters.

---

## 5. Probes

Ordered by (cutting power) / (cost), cheapest-and-most-cutting first.

### Probe 1 · {Short name} ({compute estimate})

**Hypothesis.** A prediction specific enough to be wrong. State a
direction and a magnitude.

**Protocol.** Enough detail that someone else could run it. Datasets,
models, decoding settings, metrics, pass/fail per metric.

**Falsification.** The threshold that changes your mind. Confirming
region, falsifying region, inconclusive region.

**Compute.** Hours/days on the user's actual hardware. State the
conversion from any paper-reported H100 hours.

### Probe 2 · {Short name} ({compute estimate})

(Same shape.)

Continue for each probe. Six is a reasonable maximum. More makes the
artifact harder to act on.

---

## 6. Probe ordering

| Rank | Probe | Cutting power | Cost | First-run priority |
| ---- | ----- | ------------- | ---- | ------------------ |
| 1    | ...   | High          | Low  | Yes                |
| 2    | ...   | High          | Med  | If 1 is positive   |
| ...  |       |               |      |                    |

One-sentence rationale for the order. The user with time for one
probe should get the top row.

---

## 7. Relevance to downstream decisions

Short. What does the probe set mean for the decision that brought
the claim into the artifact's scope? A deployment
choice, build-on-top-of decision, etc.

Don't inflate. "The claim is too shaky to use" is a strong result;
"the claim is tighter than it looked" is also a strong result.

---

## 8. What this is not

- Not a verdict on {the paper / method / assessment}.
- Not a review.
- Not a reproduction (yet — probes will do that).
- Not a critique of the authors.

A closing section that keeps the artifact from being quoted as a
rejection of the work.

---

## 9. Key references to follow

Three to five citations that would be worth reading next, each with
a one-line rationale. The rationale is what makes this useful — "read
X" with no reason is noise.

---

**Session note.** {Source cached at ...}. {This backwalk lives on
branch ... in ...}. {Any follow-up artifacts planned.}
