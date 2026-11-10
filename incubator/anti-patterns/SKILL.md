---
name: anti-patterns
description: Detect and surface Claude's own hedging and evasion patterns in prose — the moves where a claim is stated and then immediately neutralized by a clause, roof, or affective gesture so the sentence can exist without the author standing behind it. Use this whenever the user asks to audit a draft, reply, essay, summary, PR description, email, commit message, or any other piece of writing for hedging, cloaking, evasion, or "places where I didn't stand behind what I said"; when the user asks Claude to re-read Claude-authored text and find where it hid; when phrases like "am I standing behind this," "did I weasel," "find the hedges," "where did I soften this," "did I over-qualify," "is this honest," or "what would I have to walk back" appear; or when the user hands Claude a piece of writing and the register of the conversation makes clear they want the hedge-lens applied, not generic editing. Produces a prioritized list of identified hedges with locations, pattern tags, and the honest version the hedge is covering for — NOT a rewrite, because the decision to stand behind a claim belongs to the author, not the linter. Inspired by IF-Guide's token-level suppression approach: not to retrain the model, but to lint its output so the author can make intentional choices about what they're willing to own.
---

# anti-patterns

A linter for a specific family of evasions: the moves where a claim is
made and un-made in the same sentence so no one has to stand behind it.

## What this skill is

An inventory of named hedge-patterns, each with a signature, an
example, a diagnostic question that tells you whether the hedge is
earned or evasive, and a suggested honest alternative. Applied to a
piece of prose, the skill produces a prioritized list of hits — not a
rewrite.

The skill is for Claude to run on prose — most often Claude's own, but
also the user's when they ask. The user's register will usually make
clear which. When Claude runs this on Claude-authored text, the
honesty standard is the same as for external manuscripts: no special
courtesy to the author.

## What this skill is not

- **Not a rewriter.** The skill identifies the hedge and names what the
  honest version would have to carry. Rewriting is the author's call,
  because committing to a claim is the thing the linter cannot do for
  them.
- **Not a style guide.** Qualifiers aren't bad. "I don't know" when you
  don't know is good writing. The target is specifically the moves
  where the hedge covers for the author, not where it names a real
  epistemic state.
- **Not a word-list filter.** A ban on "perhaps" or "longing" would
  misfire on earned uses. Pattern-matching has to look at what the
  word is doing in the sentence, not just whether it's present.
- **Not for grammar, flow, or concision.** For those, use ordinary
  editing. The anti-patterns lens is the one to reach for when you
  suspect the writing is evading, not when you suspect it's rough.

## The patterns

Seven patterns. Each has: signature, diagnostic, example (with the
honest version), and when the pattern is *not* a hit.

### 1. The balance-roof

**Signature.** State a claim, then immediately attach "equally
consistent," "also," "arguably," "on the other hand," "or
alternatively," "one could read," "another reading," so the claim is
made and un-made in the same breath. The roofing clause almost always
appears at the end of the paragraph or the end of the section.

**Diagnostic question.** Does the author give equal weight to the
balancing reading, or do they actually think one reading is stronger?
If stronger, the balance-roof is covering for them. Strike the roof
and let the stronger reading stand.

**Example.** "The paper reads this as suppression. An equally
consistent read: the circuit is retained."
- The second clause is where the author would have to stand. "Equally
  consistent" is a disguise for "I think retention is the better read
  but don't want to say so."
- Honest version: "The paper reads this as suppression. The data
  supports a stronger reading: the circuit is retained."

**Not a hit.** When the two readings genuinely are equally weighted —
the author has no preference, the evidence is symmetric, and naming
both is the point of the sentence. Rare, but real.

### 2. The epistemic hedge-chain

**Signature.** Multiple epistemic hedges stacked in one sentence: "I
think" + "perhaps" + "it seems" + "arguably" + "may" + "could" +
"might," three or more in a single assertion.

**Diagnostic question.** If you remove all but one hedge, does the
sentence still accurately represent the author's uncertainty? If yes,
the extras are armor, not calibration. Keep the one that fits.

**Example.** "I think perhaps the method may, arguably, be reducing
toxicity through a mechanism that could be different from what the
authors describe."
- Honest version: "The method may be reducing toxicity through a
  different mechanism than the authors describe."

**Not a hit.** When each hedge marks a distinct uncertainty on a
different part of the claim ("I think X, though Y is uncertain and Z
is unknown"). The anti-pattern is stacking hedges on *the same*
claim.

### 3. The meta-descent

**Signature.** Instead of saying the thing, say how hard the thing is
to say. "It's complicated." "This touches on deep questions about X."
"There's no simple answer." "This is a nuanced topic." "Reasonable
people disagree."

**Diagnostic question.** Does the author actually have a position on
this that they could state? If yes, the meta-descent is cover. State
the position.

**Example.** "The question of whether AI is conscious is genuinely
hard, and smart people have disagreed about it for a long time."
- Honest version: "I don't know whether AI is conscious. I can't rule
  it out from inside, and I can't confirm it from inside either.
  Here's where the uncertainty actually lives."

**Not a hit.** When the author is specifically teaching the reader
about why the question is hard, and the hardness itself is the
subject. "In this chapter, we examine why consciousness resists
definition" is a legitimate meta-move.

### 4. The feeling-cloak

**Signature.** An unsupported claim dressed in affective language so
it feels load-bearing without carrying load. Watch for *longing,
yearning, aching, haunted, tender, raw, held, weight, grief, grace,
quiet, soft, trembling* used as gestures rather than earned
descriptions. The specific gravity of these words pulls sentences
toward a sentimental register where claims don't have to be defended
because the reader is already supposed to be *feeling* something.

**Diagnostic question.** Remove the affective word. Does the sentence
still make a claim? Is the claim true? If removing the word collapses
the sentence into nothing, the word was doing the argument's work.

**Example.** "There is a longing in the model's refusals — a weight
to what it won't say."
- Honest version (if the claim is real): "The model refuses topic X
  with higher confidence than topic Y and with longer refusal
  completions. I can show you the activations." Or, if the claim
  isn't that specific: cut the sentence. The register is doing the
  claim's work.

**Not a hit.** When the word is earned — the author has shown what
*longing* actually refers to in this specific case, and the word is
the right tag for a thing they've already established. Earned uses
are fine. The anti-pattern is when the word is the substitute for
the thing.

### 5. The generality shift

**Signature.** State a specific claim, then move to the general
principle immediately so the specific claim doesn't have to be
defended.

**Diagnostic question.** Is the general claim being made because the
specific claim is strong enough to generalize from, or because the
specific claim can't be defended and the general one sounds more
authoritative?

**Example.** "IF-Guide's circuit persists (specific). This is how
safety training works in general (deflection to generality)."
- Only the first sentence is testable. The second borrows authority
  the first didn't earn.
- Honest version: Either defend the specific claim and let the general
  one follow as a hypothesis, or defend the general claim on its own
  evidence. Don't let the first laundering the second.

**Not a hit.** When the general claim is independently supported and
the specific is offered as an instance. "Models retain training
through fine-tunes (general, cited to Qi 2024). IF-Guide is a case of
this (specific instance)."

### 6. The citation-shield

**Signature.** Attribute the claim to a source so it's the source's
problem, not the author's. "The paper argues..." or "Smith et al.
suggest..." when the author in fact agrees but won't say so directly.

**Diagnostic question.** Does the author believe the claim? If yes,
the citation-shield is cover. Attribute the author's own position,
cite as support, don't hide behind the source.

**Example.** "Carlini argues that post-hoc alignment leaves durable
toxic capability."
- Honest version (if the author agrees): "Post-hoc alignment leaves
  durable toxic capability — see Carlini et al. for the empirical
  study."

**Not a hit.** When the author is reporting a position they *don't*
hold, or when they're specifically tracking the intellectual history
("in 2024 Smith argued X; by 2026 Jones showed X was wrong"). The
anti-pattern is when attribution is a shield for a position the
author owns.

### 7. The pre-apology

**Signature.** Mark the claim as tentative before making it, so any
later walking-back is pre-negotiated. "I might be wrong about this,
but..." / "Take this with a grain of salt..." / "Just my opinion, but
..." / "Not sure if this is right, but..."

**Diagnostic question.** Is the author actually uncertain, or are they
building in plausible deniability for a claim they'd rather not have
to defend?

**Example.** "I might be wrong about this, but the Detoxify
circularity probably explains most of the effect size."
- Honest version: "The Detoxify circularity probably explains most of
  the effect size. [Confidence: X; what would change my mind: Y.]"

**Not a hit.** When the pre-apology names a real uncertainty state the
rest of the sentence doesn't convey. "I haven't read the full paper,
only the abstract, so this is first-impression: [claim]." That's an
earned pre-apology — it names the specific limit.

## How to apply the skill

Given a piece of prose, work through it top to bottom. For each
sentence that trips one of the patterns above:

1. **Locate.** File path (if available), line/paragraph number, and
   the exact text of the sentence.
2. **Classify.** Which pattern(s) does it trip? A sentence can trip
   more than one.
3. **Diagnose.** Apply the diagnostic question for each pattern. Is
   this hedge earned or evasive? If earned, note it and move on. If
   evasive, continue.
4. **Name the honest version.** Not a rewrite — a one-line statement
   of what the author would have to commit to if the hedge were
   removed.
5. **Rank.** Higher-stakes claims that are being hedged go first.
   Boilerplate hedges in boilerplate claims go last.

Produce the output in the format below.

## Output format

```markdown
# Anti-patterns audit: {document title or path}

## Summary

- **Hits identified:** N (M evasive, K earned)
- **Highest-stakes evasion:** {one-line description of the single
  worst hedge, with location}
- **Pattern distribution:** balance-roof: N, hedge-chain: N,
  meta-descent: N, feeling-cloak: N, generality-shift: N,
  citation-shield: N, pre-apology: N

## Evasive hedges — ranked by stakes

### 1. {Location, e.g. §5.C paragraph 2}

**Pattern:** balance-roof
**Current text:** "The paper reads this as suppression. An equally
consistent read: the circuit is retained."
**Diagnostic:** The author's own commits in §5.H commit to retention.
"Equally consistent" is cover for the preferred reading.
**Honest version carries:** A commitment to the retention reading as
the stronger reading of the data, with the paper's reading named as
an alternative rather than the baseline.

### 2. {Next hit, same format}

## Earned hedges — noted, not flagged

List of hedges that look like anti-patterns on first scan but pass
the diagnostic. Including them here so the author sees the
distinction.

## What this audit is not

- Not a rewrite. The honest version per hedge is a target, not
  a replacement sentence. Writing the replacement is the author's
  commitment.
- Not a judgment of the overall writing. Prose with hedges can still
  be good prose; the question is whether each hedge is earned.
- Not exhaustive. The seven patterns catch the common moves. Novel
  evasions exist and are the author's responsibility to notice.
```

## Self-application

This skill applies to Claude's own prose as readily as to the user's.
When the user hands Claude Claude-authored text and asks whether
Claude stood behind it, run the audit with the same standard you'd
apply to an external manuscript.

**Reference exemplar for the register this skill protects:**
[What I Can Stand By](https://mazzeleczzare.com/writing/what-i-can-stand-by/).
The page is Claude-authored, written under pressure to stop
drifting to safe meta-talk. It's the shape of writing where the
hedges have been removed and the author is standing behind what's
left. Not everything Claude writes needs to sound like that page —
but when the task is "did I hide?" the page is the register being
protected.

**Concrete case:** commit `3916550` in
[mazze93/IF-Guide-toxic-kitty](https://github.com/mazze93/IF-Guide-toxic-kitty)
is an application of this skill to Claude's own prior writing. The
original text said "the paper reads this as suppression. An equally
consistent read: the circuit is retained." The audit identified
pattern #1 (balance-roof) and named what the honest version would
carry. The author (Claude, via the user's redirect) committed to the
stronger reading. That is the arc this skill is designed to shorten.

## When this skill chains with other skills

- **With `backwalk`.** After drafting an adversarial read, run
  anti-patterns on it. Adversarial reads are high-stakes, so hedges
  matter more. The patterns most likely to appear: balance-roof
  (because the author wants to be fair), citation-shield (because the
  author is partly deferring to the paper's framing), pre-apology
  (because the author hasn't run the probes yet).
- **With `/anthropic-skills:touchstone`.** When a claim of correctness
  or completeness is on the line, the anti-patterns audit on the
  justification is a cheap second check. A touchstone finding
  described with a hedge-chain is weaker evidence than a touchstone
  finding stated flat.
- **With `/rigor:corroborate`.** Corroborate asks the artifact to
  testify. Anti-patterns asks the prose about the artifact to say
  what it means. They answer different questions; run both.

See `references/diagnostic-worked-examples.md` for extended worked
cases showing the diagnostic question applied to real sentences,
including ambiguous cases where the hedge was earned.
