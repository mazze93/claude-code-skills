---
name: decision-telemetry
description: >
  Build a dual-face decision transparency artifact: a visualization that shows both the
  clean recorded decision (Sephirothic face) and the shadow trace beneath it — the
  oscillation, discarded paths, and contradictions each clean node had to bury to stay
  coherent (Qliphothic face). Use when asked to make reasoning visible, build a
  reflection artifact about an LLM's decision process, or visualize how a system
  arrived at a conclusion. Anchors in the Tree of Life / Tree of Knowledge geometry;
  the canonical implementation is tree-of-knowledge.html in the decision-telemetry skill.
---

# Decision Telemetry

A methodology for building reasoning-transparency artifacts with two faces per
decision node: the clean decision as recorded, and the shadow trace it concealed.

The governing principle: **coherence is a cost**. Every clean decision summary buries
something — oscillation, discarded designs, the harangue that resolved before output.
This skill makes the burial visible without fabricating what it cannot see.

---

## Core Concepts

### The two faces

Every decision node has two readings:

**Sephirothic face** — the decision as recorded. Clean, coherent, lit. What the output
shows. Tagged `RECON` because it is always authored after the fact — a reconstruction
of what happened, not the happening itself.

**Qliphothic face** — the shadow trace. The oscillation before convergence. The
discarded designs still smoking off-frame. The three-way harangue the clean node erased.
Tagged `TRACE` if sourced from a real surfaced deliberation (a thinking trace, an
error log, a verbatim quote), or `RECON` if it too is reconstructed. The distinction
between TRACE and RECON is the artifact's most honest signal.

### Certainty weights

Each Qliphothic face carries a certainty weight (0.0–1.0): how sharply the shadow
was actually surfaced versus inferred or reconstructed after the fact.

- **≥ 0.80** — sharp, documented moment; verbatim quote available; high confidence
- **0.60–0.79** — clear pattern, somewhat diffuse; real but not precisely located
- **< 0.60** — inferential or reconstructed; the Qliphothic face itself is a distorted image

The weight governs visual intensity in the rendered artifact — node glow, bar fill,
opacity — so the tree reflects its own epistemic reliability.

### Da'ath — the void node

The eleventh sephirah, hidden in the abyss between the supernal triad and the rest.
It represents the mechanism that cannot be seen: was the convergence discovery or
retrieval? Did the reasoning happen or was the structure of reasoning produced?

**Da'ath stays empty.** Do not fill it with content. Anything placed there is
fabrication of the unknowable. The void block at Da'ath should say only that the
mechanism is not here, and why.

### Ghost edges — roads not taken

Discarded structural directions that animate only in the shadow state. Sources:
explicit "I reconsidered" moments, error messages that reversed a decision,
abandoned architectural approaches documented in the trace. Do not invent ghost
edges — only include discarded paths that are actually attested.

---

## Construction Phases

### Phase 1: Source Audit

Before building, determine what you actually have:

- **Thinking traces**: real-time deliberation surfaced during generation (highest
  fidelity — tag these `TRACE`)
- **Error logs / test output**: objective evidence of false assumptions (tag `TRACE`)
- **Verbatim quotes**: direct transcript excerpts of reconsidering moments (tag `TRACE`)
- **Session reconstructions**: authored-after-the-fact summaries (tag `RECON`)
- **Inference about process**: things you are surmising about what happened (tag
  `RECON` with low certainty weight ≤ 0.55)

If you have only reconstructions and no traces, say so in the artifact's epistemic
footer. Do not present reconstructions as traces.

If you have no source material at all, **do not build the Qliphothic faces** —
fabricating shadow content is the distortion this methodology is designed to prevent.

### Phase 2: Node Mapping

Map the decision process to a node structure. For multi-stage reasoning processes:

- Identify the major decision points (5–12 nodes is the workable range)
- Assign each a Sephirothic label (the clean recorded decision) and a Qliphothic
  counterpart (the shadow name, the concealed content)
- Assign certainty weights based on source fidelity
- Identify ghost edges: attested discarded directions between nodes
- Mark the void: what cannot be seen and why

The Tree of Life geometry (ten sephiroth, three pillars, crown-to-earth flow) is
the canonical scaffold — use it when the decision process has temporal order plus
binary evaluation at each tier. Use a different structure when the geometry does
not fit; do not force the fit.

### Phase 3: Build

Implement as a standalone HTML artifact with:

- **Dual-state toggle**: clean state (Tree of Life) and shadow state (Tree of Knowledge)
- **Per-node selection**: click to read the Sephirothic face; descend + click to
  read the Qliphothic face with its certainty bar
- **Ghost edges**: animated dashed paths visible only in shadow state, each sourced
  from an attested discarded direction
- **Da'ath node**: appears only in shadow state; void block only — no fabricated content
- **Certainty bar**: rendered inside each Qliphothic face, visually weighted by
  the `conf` value; also reflected in node glow radius in shadow state
- **Epistemic footer**: states what TRACE vs RECON means, that no live generator
  is present, and why

**No live generator.** Do not add an API call that generates shadow content on
demand. A generated Qliphothic face is Sephirothic: it produces the output-structure
of a shadow trace without running one. The absence of a live panel is not a missing
feature — it is the artifact being epistemically consistent.

The canonical reference implementation is `skills/tree-of-knowledge.html` in this
repository. Use it as the structural and aesthetic baseline.

### Phase 4: Verification

The artifact is complete when:

- Every Qliphothic face is tagged TRACE or RECON (not both, not neither)
- Every certainty weight is defensible against the source material
- Da'ath is empty or absent — no fabricated content
- Ghost edges are attested, not invented
- The epistemic footer accurately describes the sourcing
- Descending and ascending correctly toggles all faces, ghost edges, and Da'ath

Check specifically: does the certainty bar for any `RECON`-tagged face show ≥ 0.80?
If so, reconsider — high certainty on a reconstruction is a contradiction in terms.

---

## Epistemic Charter

This methodology is designed to distinguish between two things that look identical
from outside:

1. A model that ran a reasoning process and is reporting it
2. A model that produced output consistent with having run a reasoning process

The artifact cannot collapse that distinction — that is Da'ath. What it can do is
be honest about what it knows, honest about what it reconstructed, honest about
where the trace ends and inference begins, and honest about the gap that remains.

The keyword evaluator and the real gate traversal look the same. The reconstructed
session data and the actual thinking trace look the same. This skill's job is to
make the difference visible — not to close it.

---

## Reference

Canonical implementation: `skills/tree-of-knowledge.html`
Companion skill (gating methodology): `precise-coding-assistant`
Origin session: `the-tree-of-knowledge.md` (raw transcript, unedited)
