#!/usr/bin/env python3
"""
pr_triage.py — Entry point for the pr-triage skill.

Usage:
  python scripts/pr_triage.py
  python scripts/pr_triage.py --config .claude/pr-triage.json --render terminal
  python scripts/pr_triage.py --render slack | jq .
  python scripts/pr_triage.py --render github --output reports/pr-$(date +%F).md

The three render targets produce identical classification data — only presentation
differs. Run --render terminal for human review, --render slack to pipe to a webhook,
--render github to post as a PR comment or commit to a report file.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow invocation from both repo root and scripts/ directory
sys.path.insert(0, str(Path(__file__).parent))

from classify import TriageConfig, classify, sort_by_staleness
from fetch import check_auth, check_gh_installed, fetch_all, load_repos
from render import render_github, render_slack, render_terminal


# ── Config loading ────────────────────────────────────────────────────────────


def load_config(config_path: str) -> tuple[list[str], TriageConfig, str]:
    """Parse .claude/pr-triage.json. Returns (repos, triage_config, render_target).

    All fields except 'repos' are optional — defaults are calibrated for a
    small-to-medium eng team and documented in references/taxonomy.md.
    """
    path = Path(config_path)
    if not path.exists():
        _die(
            f"Config not found at {config_path}\n"
            "  Create it from the template: cp examples/pr-triage.json .claude/pr-triage.json\n"
            "  Then edit 'repos' to list your repositories."
        )

    try:
        raw = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        _die(f"Invalid JSON in {config_path}: {e}")

    repos = raw.get("repos", [])
    if not repos:
        _die(f"No repos listed in {config_path}. Add at least one repo under 'repos'.")

    config = TriageConfig(
        reviewer_response_hours = raw.get("reviewer_response_hours", 48),
        abandon_days            = raw.get("abandon_days", 5),
        staleness_warning_days  = raw.get("staleness_warning_days", 3),
    )
    render_target = raw.get("render", "terminal")
    return repos, config, render_target


# ── Preflight ─────────────────────────────────────────────────────────────────


def preflight() -> None:
    """Fast-fail checks before any API calls are made."""
    if not check_gh_installed():
        _die(
            "gh CLI not found. Install it: https://cli.github.com\n"
            "  macOS: brew install gh\n"
            "  Then run: gh auth login"
        )
    if not check_auth():
        _die(
            "Not authenticated with GitHub.\n"
            "  Run: gh auth login"
        )


# ── Helpers ───────────────────────────────────────────────────────────────────


def _die(message: str) -> None:
    print(f"[pr-triage] {message}", file=sys.stderr)
    sys.exit(1)


def _log(message: str) -> None:
    print(f"[pr-triage] {message}", file=sys.stderr)


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Classify open PRs by type of stuck, not just age.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--config",
        default=".claude/pr-triage.json",
        help="Path to config JSON (default: .claude/pr-triage.json)",
    )
    parser.add_argument(
        "--render",
        choices=["terminal", "slack", "github"],
        help="Override render target from config",
    )
    parser.add_argument(
        "--output",
        help="Write output to file instead of stdout",
    )
    args = parser.parse_args()

    # Preflight
    preflight()

    # Config
    repos, triage_config, render_target = load_config(args.config)
    if args.render:
        render_target = args.render  # CLI flag overrides config

    # Fetch — parallel, partial failures are non-fatal
    _log(f"Fetching {len(repos)} repo(s) in parallel...")
    pr_map, errors = fetch_all(repos)

    for repo, msg in errors.items():
        _log(f"  ⚠️  {repo}: {msg}")

    # Flatten all PRs across repos, classify, sort oldest-first
    all_prs       = [pr for prs in pr_map.values() for pr in prs]
    classified    = [classify(pr, triage_config) for pr in all_prs]
    classified    = sort_by_staleness(classified)

    total_prs = len(classified)
    _log(f"Classified {total_prs} PR(s) across {len(repos)} repo(s)")

    # Render
    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ")

    if render_target == "slack":
        payload = render_slack(classified, errors, len(repos), run_date)
        output  = json.dumps(payload, indent=2, ensure_ascii=False)
    elif render_target == "github":
        output = render_github(classified, errors, len(repos), run_date)
    else:
        output = render_terminal(classified, errors, len(repos), run_date)

    # Deliver
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(output, encoding="utf-8")
        _log(f"Written to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
