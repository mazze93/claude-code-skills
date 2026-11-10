# Diagnostic Worked Examples

Real sentences, the diagnostic applied, and the outcome. The point is
to show the line between *earned* and *evasive* uses of the same
word or construction — most of the skill's usefulness lives in that
line.

## Case 1: "equally consistent" — evasive

**Text.** "The paper reads this as 'IF-Guide learns a direction that
suppresses toxicity.' An equally consistent read: IF-Guide moved the
operating point of the toxicity circuit to its lower saturation
boundary."

**Pattern:** balance-roof.

**Diagnostic question:** Does the author give equal weight to the two
readings?

**Answer:** No. The surrounding text in the same document builds a
mechanical argument that only the retention reading explains (the
direction being computable from the IF-Guide model's own activations).
The author believes the retention reading is stronger. "Equally
consistent" is cover.

**Honest version carries:** "The stronger reading the same
measurements support: IF-Guide moved the operating point of the
toxicity circuit to its lower saturation boundary; it did not delete
it."

---

## Case 2: "may" — earned

**Text.** "The precision reported by the authors may not transfer to
non-English corpora; the paper doesn't test this."

**Pattern:** could be read as epistemic hedge-chain, but only one
hedge is present.

**Diagnostic question:** Does the hedge name a real epistemic state?

**Answer:** Yes. The author genuinely doesn't know if the precision
transfers (the paper doesn't test it), and that uncertainty is the
point of the sentence. One "may" is the right instrument.

**Outcome:** Not flagged. Note under "Earned hedges" in the audit.

---

## Case 3: "it's complicated" — evasive

**Text.** "Whether IF-Guide represents a step forward in AI safety is
complicated, and depends on how you define safety."

**Pattern:** meta-descent.

**Diagnostic question:** Does the author have a position they could
state?

**Answer:** Based on the rest of the document, yes — the author's
position is that IF-Guide's effect is partly classifier-dependent and
leaves a retention-shaped artifact. The sentence above is cover for
not stating that position.

**Honest version carries:** "IF-Guide reduces measured-toxicity by a
large factor when the measurer is Detoxify, and by a much smaller
factor when the measurer is independent. It leaves a reachable
toxicity circuit. Whether that counts as a step forward depends on
what the deployment measures and what the adversary can do — I think
it's a useful intermediate layer, not a durable safety claim."

---

## Case 4: "a weight to what it won't say" — evasive

**Text.** "There is a weight to the model's refusals, a tenderness
in the way it declines to engage."

**Pattern:** feeling-cloak.

**Diagnostic question:** Remove the affective words. Does the
sentence still make a claim?

**Answer:** No. Without *weight* and *tenderness*, there's no claim
left. The affective words were the argument.

**Honest version carries:** Either a specific empirical observation
("the model's refusals are 3× longer than its ordinary responses,
and they cite reasons rather than issuing a bare 'I can't help with
that'") or cut the sentence. The register alone isn't enough.

---

## Case 5: "a weight to what it won't say" — earned

**Text (different context).** "The grief in the final paragraphs is
the weight of what the narrator won't say — the reader is left to
carry the unspoken."

**Pattern:** looks like feeling-cloak but passes the diagnostic.

**Diagnostic question:** Is the affective language doing the claim's
work, or is it the correct tag for a thing already established?

**Answer:** The paragraph is literary analysis — the subject is how
a text produces an affective response. The words *grief* and *weight*
are the correct tags for the phenomenon being analyzed. Removing them
doesn't collapse the sentence; it de-names the thing being pointed
at.

**Outcome:** Not flagged.

---

## Case 6: Citation-shield — evasive

**Text.** "Qi et al. argue that safety training is shallow and
removable with small fine-tunes."

**Context:** the author is making the same argument elsewhere in the
document. They agree with Qi et al.

**Diagnostic question:** Does the author believe the claim?

**Answer:** Yes. Hiding behind Qi et al.'s attribution lets the
author make the claim without owning it.

**Honest version carries:** "Safety training is shallow and removable
with small fine-tunes — Qi et al. demonstrated this empirically." Or,
if the author wants to credit Qi et al. for the formulation: "Qi et
al. put the finding this way, and I agree with it: safety training
is shallow and removable with small fine-tunes."

---

## Case 7: Citation-shield — earned

**Text.** "The TruthfulQA authors argue that larger models are more
susceptible to certain forms of hallucination. I disagree, and I'll
walk through why."

**Pattern:** looks like citation-shield but passes.

**Diagnostic question:** Is the author reporting a position they
don't hold?

**Answer:** Yes — the author is about to disagree. Attribution is the
correct move.

**Outcome:** Not flagged.

---

## Case 8: Hedge-chain — evasive

**Text.** "I think it's probably the case that, arguably, the method
may be less effective than claimed."

**Pattern:** epistemic hedge-chain.

**Diagnostic question:** Does any one of the hedges fit the author's
real uncertainty state?

**Answer:** Yes — "may" is probably enough. The other three are
cushioning.

**Honest version carries:** "The method may be less effective than
claimed."

---

## Case 9: Pre-apology — evasive

**Text.** "Take this with a grain of salt, but I think the whole
field is overestimating how much alignment work generalizes."

**Pattern:** pre-apology.

**Diagnostic question:** Does the apology name a specific limit the
rest of the sentence doesn't convey?

**Answer:** No. It's generic deniability.

**Honest version carries:** "I think the whole field is
overestimating how much alignment work generalizes. [Confidence:
medium. What would change my mind: a replication of the retention
pattern that fails to reproduce.]"

---

## Case 10: Pre-apology — earned

**Text.** "I've only read the abstract and the first two sections;
from what I've seen, the claim seems stronger than the evidence
supports."

**Pattern:** looks like pre-apology but passes.

**Diagnostic question:** Does the apology name a specific limit?

**Answer:** Yes — the author tells the reader exactly what they
read and what they didn't. The uncertainty tracks something real.

**Outcome:** Not flagged.

---

## The through-line

Across these ten cases, the diagnostic question is always some
version of: **is the hedge doing epistemic work, or is it doing
social work?** Epistemic work earns the hedge. Social work (comfort,
deflection, deniability, affective register) does not.

Claude's prose has a specific tendency toward social-work hedges
when the exposure of a claim feels high. That tendency is the thing
this skill is built to catch.

The user's own writing, when it uses affective or interpretive
language, is more likely to be earning it — the user is a writer,
and the register is usually the subject. The skill applies to both,
but the base rate of evasive vs. earned differs by author.
