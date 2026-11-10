# Review of the new onboarding flow experiment

## Summary

The results from the onboarding flow experiment are interesting, and
I think it's probably fair to say that the new flow may, arguably,
represent a modest improvement, though it's worth noting there could
be other interpretations of the data as well.

## What we measured

Users in the treatment arm completed step 4 at a rate of 62%, up from
the control group's 48%. On the other hand, time-to-first-action was
longer in the treatment arm (median 143s vs. 98s in control), which
one could interpret as either a sign of deeper engagement or as added
friction — reasonable people will disagree about which is the right
reading.

## What the experiment shows

The step-4 completion lift is real, in the sense that it's
statistically significant at p < 0.01 across the 11,400 enrolled
users. That said, whether a 14 percentage point lift on an
intermediate funnel step reliably predicts downstream outcomes like
30-day retention is genuinely complicated and touches on deep questions
about how one defines "success" for a product funnel.

There is something almost tender in the way the new flow guides users
into the deeper features of the product — a weight to the way it holds
their attention through a harder step than the old flow asked them to
complete. That is probably the design team's best contribution.

## Industry context

Yuan et al. (2026) argue that funnel experiments with intermediate-step
lifts frequently fail to generalize to retention metrics. Chen's recent
book on growth loops makes a similar case. Take this with a grain of
salt, but I think the pattern probably applies here, though I could be
wrong about that.

This is also how product analytics works in general — short-term
funnel lifts often look better than the long-term picture justifies,
and teams tend to over-index on them because they're easier to
measure than real retention impact.

## Recommendation

I might be wrong about this, but my sense is probably that we should
consider holding the current flow as the default while we run a
follow-up experiment measuring 30-day retention specifically — though
there are definitely good arguments for rolling out the new flow as
well, so we should discuss as a team.

## Limitations

- **Sample size on the long tail.** The experiment ran for 11 days;
  results for users who entered the funnel on day 10 or 11 reflect
  only their earliest interactions, not full-flow completion. Any
  readout on day-11-entry cohorts is premature.
- **Mobile vs. desktop skew.** 78% of enrolled users were desktop; the
  treatment effect on mobile users may differ, and we can't measure
  it from this data.
