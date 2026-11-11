# Uncertainty audit: Incident 2026-11-05 writeup

## Verdict

Most of the uncertainty is earned, and there is less hedging than you think. I count about ten hedged phrases in 115 lines. Most of the doubt is carried by the "What we do not know yet" section, which leaves the facts elsewhere free to be stated flat.

Three things need work:

- **Five hedges are cover or are aimed at the wrong thing** (items 1–5). Two of them are pure filler.
- **Six confident sentences claim more than your own numbers support** (items 6–11). This is the larger risk in the document, and it runs opposite to the one you asked about.
- **The handoff is silent on current state** (last section).

The test I used: a hedge is earned when it names the specific unknown and says why the evidence in hand doesn't settle it. It is cover when it would fit any incident ("it's complicated," "can't be ruled out"), or when the question could be answered by a check nobody has run yet.

If you only fix three, fix 1, 3 and 7.

## Commit harder

### 1. Open question 4 (lines 105–108)

> The fact of the matter is this is complicated and touches on deeper questions about how we want to handle load-shedding in the checkout path. Some would argue for it, others would argue against.

This is the clearest case of cover. Neither sentence contains an argument for or against. It is also the only question owned by a team instead of a person.

The question is premature as well. A cart-size breaker only makes sense if cart size is the trigger, and question 2 hasn't established that. Either move it to the post-mortem or state the dependency:

> 4. Should `/checkout/finalize` get a per-cart-size circuit breaker? Blocked on question 2: it helps only if cart size is the trigger, and it works by rejecting large orders. Decide at the post-mortem. (Owner: Platform / *name*.)

Replace my for-and-against with the real positions if people on the team hold them.

### 2. Mitigation efficacy (lines 91–95)

> Something that may be oversimplifying but worth noting: the fact that failover resolved the symptom does not mean the cause is region-specific.

The point is correct and it is not a simplification, so the preamble apologises for nothing. Cut it and start at "The fact that failover resolved the symptom."

"Could equally be" asserts equal odds you have no basis for. "Could also be" is what you mean.

This section also undersells evidence you already have. `us-west` and `eu-central-1` presumably serve large carts too, and neither spiked. Assuming the same build runs in all three regions, cart size alone cannot be the cause. It has to be cart size plus something about `us-east`, or an unusual volume of large carts in `us-east` during the window. You can say that now.

### 3. The large-cart sample (lines 48–51 and 101)

> This is suggestive but the sample is too small to be causal.

The hedge is on the wrong thing. Sample size is not the weakness: 32 of 50 against an 11% baseline is about 12 standard deviations from chance (p ≈ 5 × 10⁻¹⁹). Large carts are over-represented in that sample, so drop "appear" on line 101 too.

The real uncertainty is elsewhere, and the writeup doesn't state it:

- **How the 50 were chosen.** A random draw from slow requests, the slowest 50, and the first 50 the on-call found would each mean something different.
- **Whether large carts are always in the slow tail.** The 11% is their share of all requests. The comparison you need is their share of slow requests on a normal day.

The finding is also filed under "What we do not know yet." Move the 32-of-50 to "What we know" and leave only the causal question behind.

### 4. The logging refactor (lines 30–33, 52–53, 62–64, 68–71, 103–104)

> A delayed effect from that change can't be ruled out but has no supporting evidence yet.

"Can't be ruled out" is true of nearly anything. The refactor appears in five sections and is named as one of two threads for the post-mortem, which gives it more weight than the evidence does.

- **You have evidence against it and don't use it.** It ran 52 hours without effect, and the incident hit one region. If it shipped to all three, say "unlikely" and give those two reasons.
- **Question 3 is cheap to answer.** Whether the change touches a synchronous path is settled by reading the diff (a diff read, not a git-blame). This is unknown because nobody has looked, which is different from unknown because the evidence is ambiguous. Give it a date before the post-mortem, or do it and delete the question.
- **The description is inconsistent.** Line 31 calls it "a minor logging refactor." Line 70 says it added logging. If it added log calls on the finalize path, "minor refactor" undersells it. Describe what it changed.

### 5. The database (lines 34–36 against line 83)

The body says the database "does not appear to be the bottleneck." The timeline says "ruled out." Pick one.

The metric you cite supports a narrower, firmer claim: pool exhaustion is ruled out. Pool saturation under 60% says nothing about slow queries or lock waits, so say whether those were checked.

## Pull back: confident sentences that outrun the numbers

### 6. "The latency carried p99 only … This rules out a general resource exhaustion" (lines 27–29)

p50 went from 0.9s to 2.1s, which is 2.3×. That is not "p99 only," and "rules out" is too strong when p50 more than doubled and all three downstream services slowed. "Argues against" is what the data supports.

This matters because line 73 ("The signal does not indicate a systemic issue") rests on it, while line 45 keeps "a shared cause we haven't identified" alive. The document can't hold both at full strength.

### 7. Error rate against timeouts (lines 15–17)

If 10% of requests exceeded the 30s client timeout, user-visible failures should be near 10%, not 1.4%. Either the 10% is wrong, or 1.4% counts something narrower than what users saw (server-side errors, for example). This number drives the severity call, so fix it before the writeup circulates.

### 8. "54 hours before the spike" (line 32)

2026-11-03 09:40 to 2026-11-05 14:12 is 52.5 hours.

### 9. Window start (lines 5 and 80)

14:12 is when the alert fired, and the alert evaluates a 10-minute window, so onset was earlier. Say "alerted at 14:12," or read the onset off the raw graph. "We don't know exactly when it started" would be earned here.

### 10. "No deploys occurred in the hour preceding the incident" (line 30)

The sentence doesn't say which services, then narrows to `checkout-finalize`. With `fulfillment-sched` as the lead suspect, its deploy and config history is the one the reader wants.

### 11. "the two threads the post-mortem will close out" (lines 62–64)

This leaves out open question 1, whether `fulfillment-sched` is cause or symptom, which is the main one.

## Earned: leave these alone

- **Line 3, the status line.** "Mitigated. Root cause investigation open." Two flat statements.
- **Lines 44–47, cause or shared cause.** It names both alternatives and says why the evidence doesn't decide ("The logs do not disambiguate"). This is the model for the rest. One addition: line 38 says all three downstream services slowed but gives numbers only for `fulfillment-sched`. Add the other two. If they barely moved, `fulfillment-sched` is the likelier cause; if they moved a lot, a shared cause is.
- **Lines 68–74, "What we are not doing."** Two firm decisions with reasons. The "may" in "logging we may need" is literal, since a recurrence may not happen.
- **Lines 95–96.** "The failover gave us time, not an answer." It tells the next shift the problem is not solved.
- **Lines 100–104, questions 1–3.** Real questions with named owners.
- **Lines 112–115, the scope note.** It says what the document does not claim.

## One absence

The scope note promises "what the team should know going into the next shift," and the writeup never says:

- where traffic is now (still on `us-west`, or failed back);
- what the failback criteria are;
- what the next shift should do if it recurs.

None of that depends on root cause. These are the sentences the next shift needs most, and they can be written without a single hedge.
