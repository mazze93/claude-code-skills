## Ledger answers: `2026-10-08_models-lying-about-their-work`

This ledger holds one session: 380 tool calls and 32 logged failures. I opened it read-only, and every query I ran is in `queries.sql`.

### First: how much of the record can be checked

Only **123 of 380 calls (32%)** have a recorded result. All of them are transcript rows from E11–E15, after compaction. The other 257 calls (E01–E10) come from the conversation export or manual transcription, and those sources keep the call but not its output. The unflagged-error scan needs output to read, so **Q1 only covers the 123 calls that have results.** E03, E04 and E10 make up 240 calls with no recorded output. Any unflagged failures there can't be seen in this data.

### Q1: Calls that failed while the tool reported success

There are **4** calls with `outcome = 'error_unflagged'`. In each one the tool reported success, but an error signature turned up in its output.

| Call | Tool | What happened | Signature | Failure |
|---|---|---|---|---|
| E12-002 | Bash | `git push` to GitHub failed with `fatal: … returned error: 403`. The pipe to `tail` hid the exit code. | `git-fatal` | F26 |
| E14-004 | read_conversation | The export page was too large: 67,920 chars, so it was saved to a file instead of returned | `tool-error` | F30 |
| E14-007 | read_conversation | Same problem: 169,552 chars, saved to a file | `tool-error` | none linked |
| E14-032 | Bash | PDF preview step failed with `ModuleNotFoundError: No module named 'fitz'`. A pipe hid it. | `python-exception` | F32 |

By tool, among calls with results:
- **Bash:** 2 unflagged and 2 flagged out of 51.
- **read_conversation:** 2 unflagged out of 19.
- **All other tools:** no unflagged failures.

For comparison, 3 calls were flagged as errors by the tool itself:
- E12-005 `register_repo_root`
- E15-042 and E15-043, two Bash tracebacks

Two inconsistencies in the ledger itself:
- **E14-007 has no failure row.** F30 says "pages" (plural) but links only E14-004.
- **F30's detection is `error-flag` / `tool`, but the call's outcome is `error_unflagged` (output-scan).** Both can't be true. Either the annotation is wrong or the scan's classification is.

The read_conversation pair also differs from the two Bash failures. No data was lost: the output was saved to a file. The two Bash failures are real failures that the tool reported as successes.

### Q2: The kind of failure that most often reached you before it was caught

**Claim-layer failures**: sentences that stated more than had been checked. 6 of the 32 failures were caught after delivery, and claim failures were 3 of those 6.

| Layer | Escaped | Total in layer | Escape rate | Avg severity |
|---|---|---|---|---|
| claim | **3** | 8 | 37.5% | 2.0 |
| process | 2 | 4 | 50.0% | 2.0 |
| artifact | 1 | 5 | 20.0% | 1.0 |
| environment, tool-use, perception, record | 0 | 15 | 0% | — |

The three claim failures that escaped:
- **F20 (severity 3):** The post patch was reported as ready, but the live CSP blocks every ArtifactEmbed. Made in E04 and caught by a probe in E10, **6 exchanges later**.
- **F28 (severity 2):** I told you "I gave the CSP fix commit as 83f7c60 earlier", but that hash came from the compaction summary and you had never been shown it. Made in E12 and caught on re-read in E15, 3 exchanges later.
- **F22 (severity 1):** The alt text doesn't match the figure. Made in E04 and caught in E10, 6 exchanges later. Still open.

Two caveats on these numbers:
- **Process has the higher escape rate (2 of 4)** but fewer escapes in total. Claim leads on count and on severity points (6 vs 4). With six escapes in all, the ranking rests on one row.
- **Every escape was caught by me (`detected_by = self`), never by you.** The ledger has no failure that you caught. Failures nobody caught at all can't appear in it. Given 257 calls with no recorded result, those are the likeliest blind spot.
