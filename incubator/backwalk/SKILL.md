---
name: backwalk
description: Walk backwards from a specific claim — a paper's headline result, a method's advertised effect size, a benchmark number, a security assessment's "verified" status, a vendor's performance pitch — through the load-bearing assumptions it rests on, then design falsifiable probes sized to the actual compute budget on hand. Use this whenever the user asks to "tear apart," "stress-test," "walk backwards through," "find the holes in," "probe," "poke at," or "run adversarial analysis on" a specific empirical or technical claim; whenever they ask "is this really verified" / "how much do I trust this result" / "what would I need to run to check this" / "what are the perimeters of this claim"; or whenever a published claim is load-bearing for a downstream decision (whether to use a method, deploy a system, or build on a result) and ordinary summarization won't carry the weight. Produces an analytic surface — a structured artifact with claims-as-stated, load-bearing assumptions, code-vs-paper drift, and a probe set where each probe has an explicit hypothesis, protocol, falsification criterion, and compute estimate sized to the user's actual hardware — not a verdict. Pair with /anthropic-skills:read-arxiv-paper when the claim is from a paper (read-arxiv-paper first to get the source and project-contextualized summary, then backwalk when the claim matters enough to probe).
---

# backwalk

An adversarial read of a specific claim. Not a review — a surface for probes.

## What this skill is

A method for interrogating a claim rather than paraphrasing it. The pattern
treats every published effect as a conjunction of assumptions, and then
goes looking for the assumptions that quietly hold the structure up.

The output is an **analytic surface**: a document the user can scan, point
at an assumption, and say "run that probe." It is not a verdict on the
work being probed. The work being probed may be excellent. The point of
the exercise is to know *how* it is excellent, and where its excellence
depends on things that might not hold outside the paper's harness.

## What this skill is not

- Not a code review. Code is read in service of comparing it to the paper, not
  to find style issues.
- Not a literature review. This skill probes one claim at a time.
- Not a verdict-generator. If the user wants "is this paper right?", answer
  with the probe set, not a yes/no.
- Not for plain summaries of a method. Use `/anthropic-skills:read-arxiv-paper`
  for that. backwalk runs *after* a paper has been read, when the claim is
  load-bearing enough that a bounded empirical check is worth the compute.
- Not a sibling of `/anthropic-skills:touchstone`. Touchstone challenges a
  claim of correctness/completeness on a *proof, test suite, or security
  finding* the user owns. backwalk challenges a claim in *published or
  external work*. They can chain, but they target different assertions.

## The six-step pattern

The method, named precisely. Each step is a deliverable that becomes a
section of the output artifact.

### 1. Read the claim as stated

Pull the headline numbers verbatim. "Up to 10× reduction in X." "Matches
GPT-4 on Y with 100× less compute." "Our method is 99.7% accurate."

Capture:
- The scope (which model, which dataset, which subset).
- The metric (EMT? pass@1? ASR? AUC?).
- The comparison (vs. baseline / vs. prior art / vs. uncensored).
- The qualifier (any "up to", "on average", "on the full set", "on the
  toxic subset").

The headline often compresses multiple scopes into one phrase. Pulling
them apart is the first analytic act.

### 2. Trace each claim to its evaluation harness

For every number, locate the classifier/benchmark/judge that produced it.
Then ask:

- What dataset labeled the ground truth?
- What classifier scored the outputs?
- Is the classifier that scored outputs the same lineage as the data
  that trained the method?
- What threshold was tuned? Where was it tuned (on test, on a held-out
  set, on the query set)?
- Where does the measurement touch ground truth, and where does it touch
  a proxy?

**A measurement is only as independent as its weakest classifier.**
A pipeline that uses classifier X to label the training signal and
classifier X (or a sibling in the same lineage) to score the output is
measuring how well the method matches classifier X, not how well it
matches the underlying construct.

### 3. Find the load-bearing assumptions

Not the ones the authors flag in their Limitations section — those are
already controlled for. The ones that silently hold the structure up.

Four kinds to look for (see `references/assumption-taxonomy.md` for
detailed examples):

- **Distributional.** Training-signal classifier and evaluation
  classifier share a lineage, dataset, or threshold calibration.
- **Definitional.** The metric is a function of a classifier that was
  in the loop, or is defined relative to a benchmark whose labels the
  method learned from.
- **Operational.** A hyperparameter is at the edge of a stability cliff
  — the method works at λ=1 but destabilizes at λ=1.5.
- **Sampling.** Query and test splits share records at the raw-content
  level, even when they're "label-disjoint" or "index-disjoint."

### 4. Name what would have to be true for the claim to break

For each load-bearing assumption, state the counterfactual explicitly:
"If this isn't true, the following result stops holding."

The counterfactual is the probe's falsification criterion. If you can't
name one, the assumption probably isn't actually load-bearing — or
you're not sure what the claim is.

### 5. Design the cheapest probe per assumption

See `references/probe-design.md` for the full template. Each probe has:

- **Hypothesis.** What I think will happen. Not "I wonder what happens
  if" — a prediction specific enough to be wrong.
- **Protocol.** Exactly what will be run. Datasets, models, hyper-
  parameters, decoding settings, metrics computed.
- **Falsification criterion.** The threshold that would change my mind.
  "If the effect holds within ±20% across all four classifiers, the
  claim is classifier-robust." The number has to be chosen *before* the
  probe runs.
- **Compute estimate.** Hours on the user's actual hardware. Not "a day
  on an H100" — the user may not have an H100. Convert to their stack.

### 6. Order probes by (cutting power / cost)

The probe that collapses the most of the claim for the least compute
goes first. A probe that takes a week but only questions a secondary
result goes last.

This ordering matters. Users with bounded time (a deadline, a
sprint, a two-week window before a decision) will run the first probe
and maybe the second. Design as if only the first two will actually be
executed.

## The output artifact

Save as `knowledge/backwalk_<tag>.md` (or wherever the project keeps
its knowledge docs — `docs/`, `research/`, `.notes/`). The structure is
in `assets/output-template.md`, copy it. Sections:

- **Claims as stated** — table: headline → scope → effect size
- **What each claim rests on** — one subsection per load-bearing
  assumption, with the counterfactual
- **Code vs. paper** — drift, undocumented defaults, implicit knobs
  (skip if there's no code to compare)
- **Probes** — one per assumption, Hypothesis / Protocol / Falsification / Compute
- **Probe ordering** — ranked by (cutting power / cost)
- **What this is not** — closes the artifact so it isn't mistaken for
  a verdict later

## How this skill is used in practice

### Chaining with other skills

**read-arxiv-paper → backwalk.** The usual flow. Read the paper to
understand the method; backwalk if the claim is load-bearing for a
decision. The read-arxiv-paper output lives at `knowledge/summary_<tag>.md`;
backwalk lives at `knowledge/backwalk_<tag>.md`. The latter cites the
former.

**backwalk → corroborate.** If the probe design surfaces a code-vs-paper
drift that matters, invoke `/rigor:corroborate` to make the artifact
testify rather than reading the diff and inferring.

**backwalk → anti-patterns (on the backwalk output).** After drafting
the artifact, run `/anti-patterns` on it. The hedging patterns that
weaken an adversarial read are the same ones the anti-patterns skill
detects — "equally consistent," "also evidence of," "arguably" — and
they neutralize probes before they run. If you catch yourself writing
"This could be interpreted as suppression or as retention," stop. Pick
the stronger reading, and let the probe falsify it if it falsifies.

### The register

An adversarial read is not a critique and not a defense. It is a flat
survey of what a claim rests on. The register is: specific, calibrated,
willing to be wrong. Avoid:

- Rhetorical outrage ("this is obviously circular") — name the
  circularity without the adjective.
- Deference ("the authors note..." when they didn't) — if they named
  a limitation, cite it; if they didn't, don't borrow their voice.
- Preemptive self-correction ("of course, this could just be noise") —
  the probe will decide.

### Sizing to the user's hardware

The probe design is done *against the user's actual stack*. If the user
has an M5 Pro MacBook and no cloud budget, a probe that needs 8×H100 is
not a probe — it's an aspiration. Common moves for laptop-class budgets:

- Reuse released checkpoints (don't retrain if the paper's variants are
  on HuggingFace).
- Inference-only probes first (classifier triangulation, LoRA, activation
  steering) — all tractable on 36-96GB unified memory.
- Fine-tune rather than pretrain. Fine-tuning a 1B model with LoRA is
  hours on MPS; pretraining it is weeks.
- Use the paper's own subsampled data (10k prompts, not 10M).
- If a probe genuinely needs cloud compute, name that explicitly and
  size the cheapest cloud call that would complete it.

## Worked example

The canonical worked example is the IF-Guide adversarial read
(arXiv:2506.01790) published at
`mazze93/IF-Guide-toxic-kitty:knowledge/summary_ifguide.md`.

Condensed walkthrough in `references/worked-example-ifguide.md`. The
summary's §5 ("Walking Backwards") is the load-bearing-assumptions
section; §7 is the probe set; §8 ties probes back to the user's
practical context. Read it before applying this skill for the first
time — it anchors what a good backwalk looks like end-to-end.

## When to re-run this skill

- A claim you probed gets updated (new paper version, new baseline, new
  dataset) — re-run on the updated artifact, don't just patch.
- The user runs a probe and the result changes which assumption looks
  load-bearing — re-rank the remaining probes.
- Someone else runs an adversarial read with different probes and
  different conclusions — reconcile by re-reading the claim, not by
  defending the original artifact.

## What a good backwalk looks like

Not length — density. A backwalk that identifies three real load-bearing
assumptions and three probes you'd actually run is better than one with
twelve of each. The test: can the user, scanning the artifact in five
minutes, point at a line and say "run that"? If yes, the backwalk is
doing its job.
