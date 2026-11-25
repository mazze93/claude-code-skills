# Incident 2026-11-05: Checkout latency spike (p99 15s → 97s)

**Status:** Mitigated. Root cause investigation open.
**Severity:** SEV-2.
**Window:** 2026-11-05 14:12 UTC — 14:47 UTC (35 min).
**Author:** Platform on-call (Claude-assisted writeup).

---

## What happened

Between 14:12 and 14:47 UTC, p99 checkout latency on `checkout-prod-us-east`
rose from a baseline of ~15s to 97s. p50 was less affected (0.9s → 2.1s).
The `/checkout/finalize` endpoint carried the increase; adjacent endpoints
(`/cart/add`, `/catalog/read`) did not. User-visible error rate rose
from 0.06% to 1.4% over the window, concentrated on the 10% of requests
that exceeded the 30s client timeout.

We mitigated at 14:47 UTC by failing over `checkout-prod-us-east`
traffic to the `us-west` replica. Latency returned to baseline within
3 minutes of the failover completing.

## What we know

- The spike was localized to one region. `us-west` and `eu-central-1`
  showed no corresponding increase.
- The latency carried p99 only. p50 moved less than 3×. This rules out
  a general resource exhaustion (which would drag p50 up with p99) and
  points at a long-tail blocker affecting a subset of requests.
- No deploys occurred in the hour preceding the incident. The last
  change to `checkout-finalize` was a minor logging refactor at 2026-11-03
  09:40 UTC, 54 hours before the spike. A delayed effect from that
  change can't be ruled out but has no supporting evidence yet.
- Database connection pool saturation metrics stayed below 60% during
  the incident window. The database itself does not appear to be the
  bottleneck.
- `checkout-finalize` fans out to three downstream services: `payments`,
  `inventory`, and `fulfillment-sched`. All three showed higher p99
  internal latency during the window, with `fulfillment-sched`
  contributing the largest increase (p99 1.2s → 68s).

## What we do not know yet

- Whether the p99 increase in `fulfillment-sched` is the cause of the
  checkout-finalize p99 increase, or whether both are downstream of a
  shared cause we haven't identified. The logs do not disambiguate
  these two possibilities.
- Whether a specific subset of requests was pathological. The on-call
  pulled 50 slow requests from the window; of those, 32 had
  cart-size > 20 items, significantly over the baseline fraction of
  11%. This is suggestive but the sample is too small to be causal.
- Whether the 2026-11-03 logging refactor contributed. A git-blame
  review of the touched files is pending the post-mortem.

## What we're doing now

- Opened a priority-1 ticket against `fulfillment-sched` to investigate
  its p99 regression and its interaction with large carts.
- Instrumented `checkout-finalize` to log cart size, downstream wait
  times per service, and request origin on all requests with total
  duration > 10s. Deployed 2026-11-05 17:30 UTC.
- Scheduled the post-mortem for 2026-11-07 10:00 UTC. The
  logging-refactor review and the large-cart hypothesis are the two
  threads the post-mortem will close out.

## What we are not doing

- We are not reverting the 2026-11-03 logging refactor until we have
  more evidence the refactor is implicated. Reverting it now would
  destroy the incremental logging it added — logging we may need to
  diagnose a recurrence.
- We are not opening a general infrastructure review beyond this
  incident. The signal does not indicate a systemic issue; it
  indicates a specific bottleneck we have not yet characterized.

## Timeline

| UTC | Event |
| --- | --- |
| 14:12 | First alert: `checkout-prod-us-east.p99 > 60s` (10-min window) |
| 14:14 | On-call paged, investigation started |
| 14:21 | Downstream wait-time graphs show `fulfillment-sched` as primary contributor |
| 14:33 | Database and app-tier resources ruled out as primary |
| 14:40 | Failover to `us-west` initiated |
| 14:47 | Failover complete; `us-east` traffic drained |
| 14:50 | p99 returns to ~15s baseline |
| 17:30 | Enhanced logging deployed to catch recurrence |

## Mitigation efficacy

The failover worked as designed. Something that may be oversimplifying
but worth noting: the fact that failover resolved the symptom does not
mean the cause is region-specific. It could equally be a cause that
happened to be localized to this region at this time (e.g., a hot
tenant, a corrupt cache state, a routing glitch). The failover gave
us time, not an answer.

## Open questions

1. Is `fulfillment-sched` the cause or a symptom? (Owner: Platform / Lia.)
2. Why do large-cart requests appear over-represented in the slow set?
   Is this a quadratic-cost path we haven't profiled? (Owner: Checkout / Tam.)
3. Does the 2026-11-03 logging refactor touch any synchronous codepath
   in `checkout-finalize`? (Owner: Checkout / Vikram.)
4. Should we add a per-cart-size circuit breaker to `/checkout/finalize`?
   The fact of the matter is this is complicated and touches on deeper
   questions about how we want to handle load-shedding in the checkout
   path. Some would argue for it, others would argue against. (Owner: Platform.)

## Scope of this writeup

This is a shift-handoff writeup, not the post-mortem. The post-mortem
will cover root cause, contributing factors, and longer-term fixes.
This document covers: what we saw, what we mitigated, and what the
team should know going into the next shift.
