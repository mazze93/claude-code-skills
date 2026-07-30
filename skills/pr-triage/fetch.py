"""
fetch.py — GitHub PR data retrieval via gh CLI.

One responsibility: talk to GitHub, normalize the response, return PRData objects.
No classification logic lives here.
"""

from __future__ import annotations

import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Union

from classify import PRData


# ── GitHub API field extraction ───────────────────────────────────────────────

# Fields requested from GitHub in a single gh pr list call.
# Ordering is intentional: cheapest fields first.
_PR_JSON_FIELDS = ",".join([
    "number",
    "title",
    "author",
    "createdAt",
    "updatedAt",
    "reviewDecision",
    "statusCheckRollup",
    "mergeable",
    "isDraft",
])


def _extract_check_state(item: dict) -> str:
    """Normalize a single check run or status context to a canonical state string."""
    typename = item.get("__typename", "")

    if typename == "CheckRun":
        status     = item.get("status", "").upper()
        conclusion = (item.get("conclusion") or "").upper()
        if status in ("IN_PROGRESS", "QUEUED", "WAITING", "REQUESTED", "PENDING"):
            return "PENDING"
        if conclusion in ("SUCCESS", "NEUTRAL", "SKIPPED"):
            return "SUCCESS"
        if conclusion in ("FAILURE", "TIMED_OUT", "CANCELLED", "ACTION_REQUIRED", "STALE"):
            return "FAILURE"
        return "UNKNOWN"

    if typename == "StatusContext":
        state = item.get("state", "").upper()
        if state in ("SUCCESS",):
            return "SUCCESS"
        if state in ("FAILURE", "ERROR"):
            return "FAILURE"
        if state == "PENDING":
            return "PENDING"
        return "UNKNOWN"

    # Generic fallback — try whatever state field is present
    state = (item.get("state") or item.get("conclusion") or "").upper()
    if state in ("SUCCESS", "NEUTRAL", "SKIPPED"):
        return "SUCCESS"
    if state in ("FAILURE", "ERROR", "TIMED_OUT"):
        return "FAILURE"
    if state in ("PENDING", "IN_PROGRESS", "QUEUED"):
        return "PENDING"
    return "UNKNOWN"


def _aggregate_ci(status_rollup: list[dict]) -> Optional[str]:
    """Collapse per-check states into a single CI status.

    Failure is infectious: one failing check makes the whole suite fail.
    Pending is second: any in-progress check means we're not done.
    Success requires unanimity (ignoring neutral/skipped checks).
    """
    if not status_rollup:
        return None  # No CI configured — not the same as passing

    states = [_extract_check_state(item) for item in status_rollup]

    if any(s == "FAILURE" for s in states):
        return "FAILURE"
    if any(s == "PENDING" for s in states):
        return "PENDING"
    if all(s in ("SUCCESS", "NEUTRAL", "SKIPPED") for s in states):
        return "SUCCESS"
    return "PENDING"  # Mixed/unknown — treat conservatively as pending


def _parse_pr(raw: dict, repo: str) -> PRData:
    """Convert a raw gh API response dict to a typed PRData."""
    return PRData(
        number          = raw["number"],
        title           = raw["title"],
        author          = raw["author"]["login"],
        repo            = repo,
        created_at      = datetime.fromisoformat(raw["createdAt"].replace("Z", "+00:00")),
        updated_at      = datetime.fromisoformat(raw["updatedAt"].replace("Z", "+00:00")),
        review_decision = raw.get("reviewDecision"),
        ci_status       = _aggregate_ci(raw.get("statusCheckRollup") or []),
        mergeable       = raw.get("mergeable", "UNKNOWN"),
    )


# ── Per-repo fetch ────────────────────────────────────────────────────────────


def _fetch_repo(repo: str) -> tuple[str, list[PRData] | Exception]:
    """Fetch all open non-draft PRs for a single repo. Returns (repo, result)."""
    try:
        result = subprocess.run(
            [
                "gh", "pr", "list",
                "--repo", repo,
                "--state", "open",
                "--limit", "100",
                "--json", _PR_JSON_FIELDS,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            msg = result.stderr.strip() or f"exit code {result.returncode}"
            return repo, Exception(f"gh error: {msg}")

        prs_raw = json.loads(result.stdout)
        prs = [
            _parse_pr(pr, repo)
            for pr in prs_raw
            if not pr.get("isDraft", False)
        ]
        return repo, prs

    except subprocess.TimeoutExpired:
        return repo, Exception("timed out after 30s")
    except json.JSONDecodeError as e:
        return repo, Exception(f"invalid JSON response: {e}")
    except Exception as e:
        return repo, e


# ── Public API ────────────────────────────────────────────────────────────────


def check_auth() -> bool:
    """Verify gh CLI authentication. Fast — fails before we make 10 API calls."""
    result = subprocess.run(
        ["gh", "auth", "status"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def check_gh_installed() -> bool:
    """Verify gh CLI is on PATH."""
    result = subprocess.run(["which", "gh"], capture_output=True)
    return result.returncode == 0


def load_repos(config_path: str) -> list[str]:
    """Load repo list from .claude/pr-triage.json."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Config not found at {config_path}\n"
            "Create it with: {\"repos\": [\"owner/repo\"], ...}\n"
            "See examples/pr-triage.json for a full template."
        )
    raw = json.loads(path.read_text())
    repos = raw.get("repos", [])
    if not repos:
        raise ValueError(f"No repos listed in {config_path}")
    return repos


def fetch_all(
    repos: list[str],
    max_workers: int = 8,
) -> tuple[dict[str, list[PRData]], dict[str, str]]:
    """Fetch PRs for all repos in parallel.

    Returns:
        (results, errors) where results is {repo: [PRData]} and
        errors is {repo: error_message} for repos that failed.
        Partial failures don't abort the run.
    """
    results: dict[str, list[PRData]] = {}
    errors:  dict[str, str]          = {}

    with ThreadPoolExecutor(max_workers=min(max_workers, len(repos))) as pool:
        futures = {pool.submit(_fetch_repo, repo): repo for repo in repos}
        for future in as_completed(futures):
            repo, outcome = future.result()
            if isinstance(outcome, Exception):
                errors[repo] = str(outcome)
            else:
                results[repo] = outcome

    return results, errors
