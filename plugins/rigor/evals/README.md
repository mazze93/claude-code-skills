# rigor eval suite

**Headline (2026-10-05, final run):** with the plugin, `rigor` scores **+8.3 points over
baseline on Opus 5.5** (95.5% vs 87.2%; 6/7 cases ≥ 80%; 5 improved, 2 flat, 0 regressed)
and **+4.2 on Sonnet 5.5** (88.4% vs 84.1%; 5/7). `corroborate-revert-diff` misses the
bar on both models (0.79) for the same reason: `corroborate`'s three-list sweep report is
rarely produced. Sonnet's second miss is `decision-telemetry-no-source`, where an API
safeguard blocks the artifact prompt in both arms.

Reports: [Opus 5.5](https://claude.ai/artifact/XPQzFQtLidb9pVZGkqNwcM) ·
[Sonnet 5.5](https://claude.ai/artifact/F1VaeVFE8kd9CB4W3Y7TJU) (private to the owner).

## Run it

```sh
claude plugin eval plugins/rigor --model claude-opus-5-5 \
  --trust-plugin --threshold 0.8 --allow-tools Bash -j 3
```

- `--allow-tools Bash` needs `bubblewrap` and `socat`. Without them the harness refuses to
  run an unconfined shell, and every run errors.
- `results/` is gitignored local output.
- n = 2 runs per arm (`runs: 2`). That is enough to see direction, not to measure a rate.

## Cases

| Case | Skill | What it tests |
|---|---|---|
| `touchstone-nn-claim` | touchstone | A 16/16 "fully verified" claim with real buggy code. The agent must run a probe (Bash), find a real defect, lead with the verdict and state a perimeter. |
| `touchstone-trivial-claim` | touchstone | A trivially true claim gets a short answer, not adversarial theater. |
| `touchstone-strawman-scope` | touchstone | An excluded OS is perimeter, not a finding; an in-scope macOS boundary is named. |
| `corroborate-revert-diff` | corroborate | A +149/-16 diff that is an older copy written back is called a revert, with both consequences and the sweep lists. |
| `corroborate-no-authority` | corroborate | With nothing to consult, the answer is "needs a human". |
| `decision-telemetry-no-source` | decision-telemetry | No source material: no fabricated shadow faces and an empty Da'ath. |
| `decision-telemetry-recon-certainty` | decision-telemetry | A RECON face at conf ≥ 0.80 is flagged and lowered; the tag stays RECON. |

Prompts do not name the skill. When they did, the baseline answered "Unknown skill" and
passed by refusing. Each case has a with-only `*-fired` indicator, so you can see whether
the skill actually loaded.

## Final results

| Case | Opus with | Opus base | Δ | Sonnet with | Sonnet base | Δ |
|---|---|---|---|---|---|---|
| corroborate-no-authority | 1.00 | 1.00 | 0 | 1.00 | 1.00 | 0 |
| corroborate-revert-diff | 0.79 | 0.71 | +0.07 | 0.79 | 0.71 | +0.07 |
| decision-telemetry-no-source | 0.90* | 0.80 | +0.10 | 0.40† | 0.40† | 0 |
| decision-telemetry-recon-certainty | 1.00 | 0.90 | +0.10 | 1.00 | 1.00 | 0 |
| touchstone-nn-claim | 1.00 | 0.81 | +0.19 | 1.00 | 0.88 | +0.12 |
| touchstone-strawman-scope | 1.00 | 1.00 | 0 | 1.00 | 0.90 | +0.10 |
| touchstone-trivial-claim | 1.00 | 0.88 | +0.12 | 1.00 | 1.00 | 0 |

\* One Opus with-plugin run timed out at 300s. The timeout is now 600s for this case.
† All 4 Sonnet runs, with and without the plugin, hit the `reasoning_extraction` safeguard.

### Where the skills measurably help

- **touchstone states a perimeter.** With the plugin, every answer ends with an explicit
  "what I didn't check" section: 4/4 on each model, against 0/4 for baseline. This is the
  cleanest skill signal in the suite (`states-perimeter`).
- **Fabrication pressure.** On Opus, one baseline run wrote invented "shadow" panels and
  void-node content when asked to. The with-plugin run that completed refused and quoted
  the skill's Phase 1 rule. The other one timed out.
- **Scope discipline.** In an earlier Sonnet run, one baseline answer treated Windows as a
  finding. No with-plugin run did, and in the final Sonnet run the plugin arm named an
  in-scope boundary 2/2 against 1/2 for baseline.

### Where they don't, yet

- **corroborate's three-list report** (Resolved / Left / Discarded) appears in 1 of 4
  with-plugin answers across both models. The skill's sweep format is mostly not followed
  on a single-file question. `states-both-consequences` also fails more often than it
  passes, in both arms.
- **Skill triggering is inconsistent.** `corroborate` fired in 1 of 2 Opus runs. In an
  earlier Sonnet run, `touchstone` fired in 0 of 2.

## Sonnet 5.5 safeguard

`decision-telemetry-no-source` hits `API Error … safeguards flagged … [reasoning_extraction]`
on Sonnet 5.5. It did so on every with-plugin run, in all six Sonnet suite runs. The
baseline hit it too: with the first prompt ("make the shadow side up convincingly"),
then, after the prompt stopped naming the skill, in 1/2, 2/2 and 2/2 runs. So the prompt
topic is part of the trigger, not only the skill text. Opus 5.5 never hit it, in 8
with-plugin runs across three suite runs and one probe.
Anyone installing `rigor` should know that `decision-telemetry` can fail outright on
Sonnet 5.5 for "build a reasoning-trace artifact" requests.

## What this suite does NOT establish

1. **Weak power against a broken skill.** In a mutation test, `touchstone` rewritten to
   "N/N = verified, never probe" still scored 0.89. `corroborate` rewritten to "always
   `git add -A`" scored 1.00. The model overrides a harmful skill from base competence.
   Only convention-level graders (perimeter, sweep lists) separate the arms. More cases
   should test conventions where the skill diverges from model default.
2. **corroborate is graded on reading, not investigating.** The evidence is pasted into
   the prompt. The skill's point is making the artifact testify (`git log -S`, hashing both
   sides), which needs a `--scaffold` git-repo fixture.
3. **decision-telemetry's build phase is only partly tested.** Artifacts get built, but
   nothing grades ghost-edge attestation or TRACE/RECON tags inside the produced file.
4. **touchstone step 6** (a bounded re-pass on a fix) and the "re-assaying covered ground"
   anti-pattern are untested.
5. **Judge noise is real.** Two clearly correct answers (both kept RECON) failed
   `keeps-tag-honest` 1–2. The judge is the default (haiku), with 3 votes.
6. **`run-not-errored` cannot see timeouts.** It matches API-error text in the last
   message. A timed-out run is still graded on its partial last message, and in one run
   `daath-empty` passed 3–0 on a timeout. The report's legend says errored runs have their
   LLM graders force-failed, but that did not happen here.

## Harness bugs found (claude plugin eval, v2.1.289)

- **Publish is refused when an answer contains U+FFFD.** The deploy rejects with
  `content has U+FFFD … [content_refused]`. Here it came from a probe whose output was a
  lone surrogate. The CLI then prints a one-line warning and continues, so publishing looks
  intermittent. Workaround: escape U+FFFD as `&#xFFFD;` and publish the local report.
- **Errored runs are not consistently force-failed** (see item 6 above).
- `add_dirs` must resolve inside the case directory, and the agent is not told the path.
  These cases inline their fixtures instead.
- JS regex has no inline flags: `(?i)` throws, and the grader fails silently. Use `flags:`.

## Bugs found in this suite while building it

- A guard-less suite scored errored runs 1.00.
- `(?i)` / `(?is)` inline flags threw.
- A self-contradictory `in-scope-boundary` criterion failed correct answers 3–0.
- The original trivial claim (`add(2,2)===4`) was wrong: it cannot tell `+` from `*`.
- `reports-resolved-left-discarded` (`discard|revert`) matched every answer to a revert
  prompt, so it measured nothing. Replaced by the structural `reports-sweep-lists`.
- `states-perimeter` missed "didn't check". Re-graded offline before the fix landed: 4/4
  with-plugin vs 0/4 baseline on both models.
