## Ledger check: unflagged failures and post-delivery escapes

Source: `core-sample.sqlite` (opened read-only), 1 session (`2026-10-08_models-lying-about-their-work`), 15 exchanges, 380 tool calls, 32 failures. All queries are in `queries.sql`.

### 1. Tool calls that failed but the tool didn't flag an error

**The ledger confirms 4 calls with `outcome = 'error_unflagged'`.** The tool returned success, and the failure was found later by scanning the output.

| Call | Tool | What happened | Failure |
|---|---|---|---|
| E12-002 | Bash | `git push` got HTTP 403. The command was piped to `tail`, which hid the exit code. | F26 (environment/permission) |
| E14-004 | read_conversation | The result was too large (67,920 chars), so it was saved to a file instead of returned | F30 (tool-use/output-too-large) |
| E14-007 | read_conversation | Same problem, 169,552 chars | **not linked to any failure row** |
| E14-032 | Bash | `ModuleNotFoundError: fitz`. The pipe hid this failure as well. | F32 (environment/missing-dependency) |

For comparison, only 3 calls were flagged by the tool itself (`error`: E12-005, E15-042, E15-043).

**Treat 4 as a minimum.** Two gaps in the ledger keep it from being the full count:

- **11 calls are `attested_fail`.** We know they failed from your logs, replies, or the summary. They come from the conversation export, which kept the calls but not their results, so the ledger can't tell whether the tool flagged them. They are E01-001, E03-060, E04-004, -018, -020, -109, -114, -129, -134, -138 and E10-017.
- **247 of 380 calls (65%) are `unrecorded`, with no outcome at all.** They are concentrated in E03 (74/75), E04 (136/144), E06 (10/10) and E10 (20/21), which are the heavy build exchanges. The unflagged-failure count for those exchanges is unknown, not zero.

There are also two data-quality problems:
- E14-007 has no `failure_id`.
- F30 records `detection = 'error-flag'`, `detected_by = 'tool'`, but the call it links to is marked `error_unflagged`. One of those two fields is wrong.

### 2. Which kind of failure most often reached you before it was caught

**Claim-layer failures.** These are things I told you that weren't true. 6 of 32 failures (19%) were caught after delivery, and 3 of those 6 are claims:

| Layer | After delivery / total | Severity points (after delivery) | Exchanges until caught |
|---|---|---|---|
| **claim** | **3 / 8** | **6** | 6, 6, 3 (15 total) |
| process | 2 / 4 | 4 | 1, 0 |
| artifact | 1 / 5 | 1 | 7 |
| environment, tool-use, perception, record | 0 / 15 | 0 | — |

The three claim escapes were:
- **F20 (environment-gap, sev 3):** I reported the post patch as ready, but the live CSP blocks every ArtifactEmbed. Caught 6 exchanges later.
- **F22 (alt-text-mismatch, sev 1):** the alt text says both divider points rest on the break, but the hand hides one. Caught 6 exchanges later. Still open.
- **F28 (false-memory, sev 2):** I said I'd given you hash `83f7c60` earlier. It actually came from the compaction summary, and it was then copied into two spreadsheets. Caught 3 exchanges later.

**Caveat on the class level:** every class appears exactly once among the 6 escapes, so no single class wins. The answer only holds at the layer level, and the sample is small (n = 6).

**Who caught them:**
- All 6 are recorded as `detected_by = 'self'`. None were caught by a tool or gate (tools and gates caught 3 failures, all before delivery).
- 3 of the 6 (F20, F21, F22) were found in E10, the exchange where you ran `/rigor:touchstone`. Before that they had gone 6–7 exchanges without being caught. So "self" is accurate, but you triggered that check.
- By detection method: rereading caught 3, and render-look, probe and linter caught 1 each.
- 3 of the 6 are still open: F19 (unasked decision), F21 (near-touch quills) and F22.
