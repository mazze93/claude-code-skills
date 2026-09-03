---
name: pr-triage
description: Triage open GitHub pull requests across one or all mazze93 repos by *what kind of stuck* they are (merge conflict, failing CI, changes requested, awaiting review, abandoned, ready-to-merge, healthy) rather than just sorting by age. Use when asked to "triage PRs", "what PRs need attention", "find stuck/stale/abandoned PRs", "which PRs are ready to merge", or to generate a PR status report for terminal, Slack, or a GitHub comment/markdown file.
---

# pr-triage

## What this is

`run-pr-triage.sh` discovers every `mazze93` repo with at least one open PR, classifies each PR by *why* it's stuck (not just how old it is), and prints a report. The point is actor-oriented triage: every stuck PR is tagged with who needs to act next (`author`, `reviewer`, `ci`, or nobody/unknown), so the output is a to-do list, not just a status board.

## Usage

```bash
skills/pr-triage/run-pr-triage.sh                     # terminal report (default)
skills/pr-triage/run-pr-triage.sh --render slack       # Slack Block Kit JSON — pipe to a webhook
skills/pr-triage/run-pr-triage.sh --render github       # GitHub-flavored markdown — post as a PR comment
skills/pr-triage/run-pr-triage.sh --output report.md    # write to a file instead of stdout
```

Requires `gh` (authenticated) and `python3` on PATH — both are checked up front and the script fails fast with an install/auth hint if either is missing.

`run-pr-triage.sh` auto-discovers repos: it lists every repo under `mazze93`, keeps only the ones with open PRs, and builds a temp config on the fly — no setup needed for the common case. To scope a run to specific repos instead, invoke the Python entry point directly with your own config:

```bash
PYTHONPATH=skills/pr-triage python3 skills/pr-triage/pr_triage.py --config path/to/config.json --render terminal
```

Config JSON shape (`repos` is the only required field):

```json
{
  "repos": ["mazze93/some-repo", "mazze93/another-repo"],
  "reviewer_response_hours": 48,
  "abandon_days": 5,
  "staleness_warning_days": 3,
  "render": "terminal"
}
```

## Classification taxonomy

Every PR gets exactly one `StuckType` (see `classify.py` for the precedence order — conflict and CI blockers are checked before review state):

| StuckType | Meaning | Who acts |
|---|---|---|
| `ABANDONED` | No activity for `abandon_days` (default 5) | unclear — triage ownership first |
| `BLOCKED_ON_CONFLICT` | Merge conflicts | author (rebase) |
| `BLOCKED_ON_CI` | Failing checks | author (investigate) |
| `BLOCKED_ON_AUTHOR` | Changes requested, no new commits since | author |
| `BLOCKED_ON_REVIEWER` | Awaiting review past `reviewer_response_hours` (default 48h) | reviewer (ping) |
| `READY_TO_MERGE` | Approved, CI green, no conflicts | nobody — merge it |
| `HEALTHY` | Active, no blockers yet | nobody |

Severity (`HIGH`/`MEDIUM`) escalates once a PR has been stuck past `staleness_warning_days` (default 3). The terminal report's "Needs Action" section surfaces `HIGH`-severity PRs first.

## Architecture

- `fetch.py` — talks to GitHub via `gh pr list` (parallel across repos, `ThreadPoolExecutor`), normalizes into `PRData`. No classification logic here.
- `classify.py` — pure functions, no I/O: `PRData` + `TriageConfig` in, `PRClassification` out. This is where the taxonomy above is actually implemented; extend it here if you need a new stuck type.
- `render.py` — three renderers (`render_terminal`, `render_slack`, `render_github`) over the same `PRClassification` list; presentation only, never re-derives classification.
- `pr_triage.py` — CLI entry point: config loading, preflight (`gh`/`python3`/auth checks), orchestration, output delivery.
- `run-pr-triage.sh` — the actual entry point for day-to-day use; wraps `pr_triage.py` with automatic repo discovery so there's no config file to maintain.

Partial failures are non-fatal: if `gh pr list` fails for one repo, `fetch_all` logs a warning and continues with the rest.
