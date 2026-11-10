# incubator

Skills under evaluation. **Nothing here ships.** `skills/` is for skills a plugin
claims; `scripts/validate_marketplace.py` rejects anything in `skills/` that belongs to
no plugin. A skill that has not yet shown it helps has no plugin to belong to, so it
waits here. The storefront and the bootstrap do not read this directory.

## What is here

| Skill | State | Evidence |
|---|---|---|
| `backwalk` | Iteration 1 run and reviewed. **No measured benefit yet.** | `backwalk-workspace/iteration-1/` |
| `anti-patterns` | Drafted. 2 of 6 iteration-1 runs landed; the rest hit a usage limit. | `anti-patterns-workspace/iteration-1/` |

### backwalk

A claim-audit skill: start from a headline conclusion, work backward to the evidence and
assumptions carrying it, then propose checks that could change the reader's confidence.

Iteration 1, three paired cases, one run per case per arm:

| Measure | With skill | Without |
|---|---|---|
| Rubric checks passed | 13/13 | 13/13 |
| Mean run time | 412 s | 242 s |
| Mean reported tokens | 155,539 | 125,850 |
| Mean output length | 4,441 words | 2,585 words |

Both arms cleared every rubric item, so the rubric has no headroom to show whether the
extra 70% time and 72% words improved anyone's judgment. This is an exploratory
comparison: n = 1 per cell, and the executor model was not recorded at run time (the
session was configured for `claude-opus-4-7` on 2026-11-07, and a sibling grader's API
error named that model; that is inference, not a log).

Owner's review of the packet (2026-11-10) set the direction for iteration 2:

1. **Make the first check the product.** Open with the exact claim, the assumption
   carrying it, the cheapest check that could change confidence, and how to read each
   outcome. Keep the full trace underneath.
2. **Grade whether the check can distinguish explanations.** Reward an output that says
   what its first check does and does not separate, cites evidence per concern, and
   names what stays unresolved. Add one case where the headline is well supported and
   one where the evidence cannot separate the explanations, to test calibration.
3. **Run a blind paired review before expanding the suite.** Same six outputs, arm names
   and grades hidden. "Which answer would help you choose what to verify next, and what
   evidence in the answer makes it better?" Record ties and time to choose.

Known defects in what is committed:

- `references/worked-example-ifguide.md` is a first pass that later review found five
  errors in. The file now opens with a note listing them. It is otherwise unchanged
  because the iteration-1 outputs were generated against it.
- The outputs break the skill's own density rule ("six probes is a reasonable maximum";
  one run produced seven).
- One `grading.json` (`paper-matches-gpt4-claim/without_skill`) was graded by the skill's
  author after the grader run hit a usage limit. The other five came from independent
  grader runs.

Tested revision: content hash `159c7854c1bf48f3` (SKILL.md, references, assets). The
committed files differ from it in three phrases of personal context removed before
publishing here, plus the note at the top of the worked example. No instruction changed.

### anti-patterns

A linter for hedging in prose: seven named patterns, each with a diagnostic question that
separates an earned hedge from an evasive one. It reports; it does not rewrite.

Not yet evaluated. Two of six runs finished. What they already show:

- **The skill looks in one direction only.** It hunts under-claiming. The baseline run on
  the incident writeup also found over-claiming: "rules out" where the numbers do not
  rule anything out, and "54 hours" where the fixture's own timestamps give 52.5. The
  second of those is an arithmetic error in the fixture that nobody planted. A skill
  about standing behind what is claimed should catch a confident sentence that outruns
  its evidence. This one does not.
- The eval design repeats what iteration 1 of `backwalk` got wrong: labelled arms, one run
  per cell, assertions a strong baseline may clear unaided. It should go to a blind
  paired review before more runs are spent on it.

## Promotion path

When a skill has evidence that it helps:

1. `git mv incubator/<name> skills/<name>`
2. Add it to a plugin in `.claude-plugin/skill-map.json` (both of these fit `rigor`).
3. `python3 scripts/build_marketplace.py`, then `python3 scripts/validate_marketplace.py`.
4. Convert its cases from the skill-creator layout here (`prompt.md`, `case.yaml`,
   `graders/*.md`) to the plugin eval layout (`plugins/<plugin>/evals/<case>/case.yaml`
   with `execution.prompt` and inline `graders`).

Until then, do not symlink these into `~/.claude/skills`.
